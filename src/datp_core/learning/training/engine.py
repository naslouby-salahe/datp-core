"""Shared centralized, FedAvg, FedProx, and Ditto training engine."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from flwr.server.strategy.aggregate import aggregate

from datp_core.core.seeding import Seed
from datp_core.learning.checkpoints.codec import (
    CapturedCheckpoint,
    ClientModelState,
    ModelState,
    PersonalizedCapturedCheckpoint,
    capture_model_state,
    load_model_state,
    ndarrays_to_state,
    state_to_ndarrays,
)
from datp_core.learning.contracts.enums import LoaderBranch, NormalizationKind, TrainingAlgorithm
from datp_core.learning.contracts.model import AdamOptimizerProfile, BatchingProfile, DenseAutoencoderProfile
from datp_core.learning.contracts.training import (
    CentralizedTrainingProfile,
    DittoTrainingProfile,
    FedAvgTrainingProfile,
    FedProxTrainingProfile,
)
from datp_core.learning.model.autoencoder import build_autoencoder
from datp_core.learning.model.runtime import (
    SeedComponent,
    SeedDerivationProfile,
    TorchRuntime,
    derive_execution_seed,
)
from datp_core.learning.training.local import LocalTrainingRequest, reconstruction_loss, train_local_autoencoder


@dataclass(frozen=True, slots=True)
class ClientTensor:
    client_id: str
    tensor: torch.Tensor


@dataclass(frozen=True, slots=True)
class RoundMetric:
    round_number: int
    global_calibration_loss: float
    personalized_calibration_loss: float | None


@dataclass(frozen=True, slots=True)
class LoaderSeedRecord:
    round_number: int
    client_id: str
    local_epoch_index: int
    branch: LoaderBranch
    shuffle_seed: Seed
    worker_seed: Seed


@dataclass(frozen=True, slots=True)
class CommonExecutionRequest:
    architecture: DenseAutoencoderProfile
    optimizer: AdamOptimizerProfile
    batching: BatchingProfile
    checkpoint_rounds: tuple[int, ...]
    total_rounds: int
    training_seed: Seed
    seed_derivation: SeedDerivationProfile
    runtime: TorchRuntime
    training_clients: tuple[ClientTensor, ...]
    calibration_clients: tuple[ClientTensor, ...]


@dataclass(frozen=True, slots=True)
class CentralizedExecutionRequest:
    common: CommonExecutionRequest
    profile: CentralizedTrainingProfile


@dataclass(frozen=True, slots=True)
class FedAvgExecutionRequest:
    common: CommonExecutionRequest
    profile: FedAvgTrainingProfile


@dataclass(frozen=True, slots=True)
class FedProxExecutionRequest:
    common: CommonExecutionRequest
    profile: FedProxTrainingProfile
    proximal_coefficient: float


@dataclass(frozen=True, slots=True)
class DittoExecutionRequest:
    common: CommonExecutionRequest
    profile: DittoTrainingProfile
    personalization_weight: float


ExecutionRequest = (
    CentralizedExecutionRequest | FedAvgExecutionRequest | FedProxExecutionRequest | DittoExecutionRequest
)


@dataclass(frozen=True, slots=True)
class TrainingResult:
    algorithm: TrainingAlgorithm
    model_initialization_seed: Seed
    round_metrics: tuple[RoundMetric, ...]
    global_checkpoints: tuple[CapturedCheckpoint, ...]
    personalized_checkpoints: tuple[PersonalizedCapturedCheckpoint, ...]
    loader_seeds: tuple[LoaderSeedRecord, ...]


class LearningError(Exception):
    """Base learning package error."""


class LearningConfigurationError(LearningError):
    """Invalid resolved learning configuration."""


class LearningDataError(LearningError):
    """Invalid materialized learning data."""


class LearningRuntimeError(LearningError):
    """Learning execution failure."""


class FederatedTrainingEngine:
    def execute(self, request: ExecutionRequest) -> TrainingResult:
        self._validate_common(request.common)
        match request:
            case CentralizedExecutionRequest():
                return self._execute_centralized(request)
            case FedAvgExecutionRequest():
                return self._execute_federated(request, proximal_coefficient=None)
            case FedProxExecutionRequest():
                if request.proximal_coefficient not in tuple(
                    float(value) for value in request.profile.proximal_coefficients
                ):
                    raise LearningConfigurationError(
                        "Resolved FedProx coefficient is absent from the configured coefficient grid"
                    )
                return self._execute_federated(request, proximal_coefficient=request.proximal_coefficient)
            case DittoExecutionRequest():
                if request.personalization_weight not in tuple(
                    float(value) for value in request.profile.personalization_weights
                ):
                    raise LearningConfigurationError(
                        "Resolved Ditto weight is absent from the configured personalization grid"
                    )
                return self._execute_ditto(request)
        raise LearningConfigurationError("Unsupported learning execution request")

    def _execute_centralized(self, request: CentralizedExecutionRequest) -> TrainingResult:
        common = request.common
        initialization_seed = self._initialization_seed(common)
        model = build_autoencoder(
            common.architecture,
            self._input_dimension(common.training_clients),
            int(initialization_seed),
            common.runtime,
        )
        pooled_training = torch.cat(tuple(client.tensor for client in common.training_clients), dim=0)
        pooled_calibration = torch.cat(tuple(client.tensor for client in common.calibration_clients), dim=0)
        metrics: list[RoundMetric] = []
        checkpoints: list[CapturedCheckpoint] = []
        seeds: list[LoaderSeedRecord] = []

        for round_number in range(1, common.total_rounds + 1):
            epoch_seeds, worker_seeds, evidence = self._seeds(
                common,
                round_number,
                "centralized",
                int(request.profile.local_epochs),
                LoaderBranch.CENTRALIZED,
            )
            seeds.extend(evidence)
            result = train_local_autoencoder(
                LocalTrainingRequest(
                    model=model,
                    training_tensor=pooled_training,
                    local_epochs=int(request.profile.local_epochs),
                    epoch_seeds=tuple(int(value) for value in epoch_seeds),
                    worker_seeds=tuple(int(value) for value in worker_seeds),
                    architecture=common.architecture,
                    optimizer=common.optimizer,
                    batching=common.batching,
                    runtime=common.runtime,
                    proximal_reference=None,
                    proximal_coefficient=None,
                )
            )
            load_model_state(model, result.state)
            loss = reconstruction_loss(
                model,
                pooled_calibration,
                common.architecture,
                common.batching,
                common.runtime,
            )
            metrics.append(RoundMetric(round_number, loss, None))
            if round_number in common.checkpoint_rounds:
                checkpoints.append(CapturedCheckpoint(round_number, capture_model_state(model)))

        return TrainingResult(
            algorithm=TrainingAlgorithm.CENTRALIZED,
            model_initialization_seed=initialization_seed,
            round_metrics=tuple(metrics),
            global_checkpoints=tuple(checkpoints),
            personalized_checkpoints=(),
            loader_seeds=tuple(seeds),
        )

    def _execute_federated(
        self,
        request: FedAvgExecutionRequest | FedProxExecutionRequest,
        proximal_coefficient: float | None,
    ) -> TrainingResult:
        common = request.common
        if common.architecture.normalization is NormalizationKind.BATCH_NORMALIZATION:
            raise LearningConfigurationError(
                "Federated dense autoencoder profiles must not aggregate BatchNorm state"
            )
        initialization_seed = self._initialization_seed(common)
        global_model = build_autoencoder(
            common.architecture,
            self._input_dimension(common.training_clients),
            int(initialization_seed),
            common.runtime,
        )
        metrics: list[RoundMetric] = []
        checkpoints: list[CapturedCheckpoint] = []
        seeds: list[LoaderSeedRecord] = []
        local_epochs = int(request.profile.local_epochs)

        for round_number in range(1, common.total_rounds + 1):
            round_start = capture_model_state(global_model)
            local_states: list[tuple[int, ModelState]] = []
            for client in common.training_clients:
                local_model = build_autoencoder(
                    common.architecture,
                    int(client.tensor.shape[1]),
                    int(initialization_seed),
                    common.runtime,
                )
                load_model_state(local_model, round_start)
                epoch_seeds, worker_seeds, evidence = self._seeds(
                    common,
                    round_number,
                    client.client_id,
                    local_epochs,
                    LoaderBranch.GLOBAL,
                )
                seeds.extend(evidence)
                local_result = train_local_autoencoder(
                    LocalTrainingRequest(
                        model=local_model,
                        training_tensor=client.tensor,
                        local_epochs=local_epochs,
                        epoch_seeds=tuple(int(value) for value in epoch_seeds),
                        worker_seeds=tuple(int(value) for value in worker_seeds),
                        architecture=common.architecture,
                        optimizer=common.optimizer,
                        batching=common.batching,
                        runtime=common.runtime,
                        proximal_reference=round_start if proximal_coefficient is not None else None,
                        proximal_coefficient=proximal_coefficient,
                    )
                )
                local_states.append((int(client.tensor.shape[0]), local_result.state))
            aggregated_state = self._aggregate_states(round_start, tuple(local_states))
            load_model_state(global_model, aggregated_state)
            global_loss = self._weighted_loss(global_model, common.calibration_clients, common)
            metrics.append(RoundMetric(round_number, global_loss, None))
            if round_number in common.checkpoint_rounds:
                checkpoints.append(CapturedCheckpoint(round_number, capture_model_state(global_model)))

        algorithm = TrainingAlgorithm.FEDPROX if proximal_coefficient is not None else TrainingAlgorithm.FEDAVG
        return TrainingResult(
            algorithm=algorithm,
            model_initialization_seed=initialization_seed,
            round_metrics=tuple(metrics),
            global_checkpoints=tuple(checkpoints),
            personalized_checkpoints=(),
            loader_seeds=tuple(seeds),
        )

    def _execute_ditto(self, request: DittoExecutionRequest) -> TrainingResult:
        common = request.common
        if common.architecture.normalization is NormalizationKind.BATCH_NORMALIZATION:
            raise LearningConfigurationError("Ditto global aggregation must not aggregate BatchNorm state")
        initialization_seed = self._initialization_seed(common)
        global_model = build_autoencoder(
            common.architecture,
            self._input_dimension(common.training_clients),
            int(initialization_seed),
            common.runtime,
        )
        initial_state = capture_model_state(global_model)
        personalized_states = tuple(
            ClientModelState(client_id=client.client_id, state=initial_state)
            for client in common.training_clients
        )
        metrics: list[RoundMetric] = []
        global_checkpoints: list[CapturedCheckpoint] = []
        personalized_checkpoints: list[PersonalizedCapturedCheckpoint] = []
        seeds: list[LoaderSeedRecord] = []

        for round_number in range(1, common.total_rounds + 1):
            round_start = capture_model_state(global_model)
            local_global_states: list[tuple[int, ModelState]] = []
            updated_personalized: list[ClientModelState] = []
            for client in common.training_clients:
                global_model_copy = build_autoencoder(
                    common.architecture,
                    int(client.tensor.shape[1]),
                    int(initialization_seed),
                    common.runtime,
                )
                load_model_state(global_model_copy, round_start)
                global_epoch_seeds, global_worker_seeds, global_evidence = self._seeds(
                    common,
                    round_number,
                    client.client_id,
                    int(request.profile.global_local_epochs),
                    LoaderBranch.GLOBAL,
                )
                seeds.extend(global_evidence)
                global_result = train_local_autoencoder(
                    LocalTrainingRequest(
                        model=global_model_copy,
                        training_tensor=client.tensor,
                        local_epochs=int(request.profile.global_local_epochs),
                        epoch_seeds=tuple(int(value) for value in global_epoch_seeds),
                        worker_seeds=tuple(int(value) for value in global_worker_seeds),
                        architecture=common.architecture,
                        optimizer=common.optimizer,
                        batching=common.batching,
                        runtime=common.runtime,
                        proximal_reference=None,
                        proximal_coefficient=None,
                    )
                )
                local_global_states.append((int(client.tensor.shape[0]), global_result.state))

                personalized_model = build_autoencoder(
                    common.architecture,
                    int(client.tensor.shape[1]),
                    int(initialization_seed),
                    common.runtime,
                )
                load_model_state(
                    personalized_model,
                    self._client_state(personalized_states, client.client_id),
                )
                personalized_epoch_seeds, personalized_worker_seeds, personalized_evidence = self._seeds(
                    common,
                    round_number,
                    client.client_id,
                    int(request.profile.personalized_local_epochs),
                    LoaderBranch.PERSONALIZED,
                )
                seeds.extend(personalized_evidence)
                personalized_result = train_local_autoencoder(
                    LocalTrainingRequest(
                        model=personalized_model,
                        training_tensor=client.tensor,
                        local_epochs=int(request.profile.personalized_local_epochs),
                        epoch_seeds=tuple(int(value) for value in personalized_epoch_seeds),
                        worker_seeds=tuple(int(value) for value in personalized_worker_seeds),
                        architecture=common.architecture,
                        optimizer=common.optimizer,
                        batching=common.batching,
                        runtime=common.runtime,
                        proximal_reference=round_start,
                        proximal_coefficient=request.personalization_weight,
                    )
                )
                updated_personalized.append(
                    ClientModelState(client_id=client.client_id, state=personalized_result.state)
                )
            personalized_states = tuple(updated_personalized)
            aggregated_state = self._aggregate_states(round_start, tuple(local_global_states))
            load_model_state(global_model, aggregated_state)
            global_loss = self._weighted_loss(global_model, common.calibration_clients, common)
            personalized_loss = self._weighted_personalized_loss(
                personalized_states,
                common.calibration_clients,
                common,
                int(initialization_seed),
            )
            metrics.append(RoundMetric(round_number, global_loss, personalized_loss))
            if round_number in common.checkpoint_rounds:
                global_state = capture_model_state(global_model)
                global_checkpoints.append(CapturedCheckpoint(round_number, global_state))
                personalized_checkpoints.append(
                    PersonalizedCapturedCheckpoint(
                        round_number=round_number,
                        global_state=global_state,
                        client_states=personalized_states,
                    )
                )

        return TrainingResult(
            algorithm=TrainingAlgorithm.DITTO,
            model_initialization_seed=initialization_seed,
            round_metrics=tuple(metrics),
            global_checkpoints=tuple(global_checkpoints),
            personalized_checkpoints=tuple(personalized_checkpoints),
            loader_seeds=tuple(seeds),
        )

    def _validate_common(self, common: CommonExecutionRequest) -> None:
        if common.total_rounds < 1:
            raise LearningConfigurationError("Training requires a positive round count")
        if not common.checkpoint_rounds:
            raise LearningConfigurationError("Training requires checkpoint capture rounds")
        if any(round_number < 1 or round_number > common.total_rounds for round_number in common.checkpoint_rounds):
            raise LearningConfigurationError("Checkpoint rounds must fall within the configured round budget")
        if tuple(sorted(common.checkpoint_rounds)) != common.checkpoint_rounds:
            raise LearningConfigurationError("Checkpoint rounds must be sorted")
        if len(set(common.checkpoint_rounds)) != len(common.checkpoint_rounds):
            raise LearningConfigurationError("Checkpoint rounds must be unique")
        training_ids = tuple(client.client_id for client in common.training_clients)
        calibration_ids = tuple(client.client_id for client in common.calibration_clients)
        if not training_ids:
            raise LearningDataError("Training requires at least one client")
        if training_ids != tuple(sorted(training_ids)) or calibration_ids != tuple(sorted(calibration_ids)):
            raise LearningDataError("Learning clients must be deterministically sorted")
        if training_ids != calibration_ids:
            raise LearningDataError("Every training client requires a matching calibration client")
        if len(set(training_ids)) != len(training_ids):
            raise LearningDataError("Learning client identifiers must be unique")
        input_dimension = self._input_dimension(common.training_clients)
        for client in (*common.training_clients, *common.calibration_clients):
            if client.tensor.ndim != 2 or int(client.tensor.shape[0]) < 1:
                raise LearningDataError("Every learning client requires a non-empty two-dimensional tensor")
            if int(client.tensor.shape[1]) != input_dimension:
                raise LearningDataError("Every learning client must use the same input dimension")
            if not torch.isfinite(client.tensor).all():
                raise LearningDataError(f"Client '{client.client_id}' contains non-finite feature values")

    def _initialization_seed(self, common: CommonExecutionRequest) -> Seed:
        return derive_execution_seed(
            common.seed_derivation.model_initialization,
            int(common.seed_derivation.digest_bytes),
            (
                SeedComponent("training_seed", int(common.training_seed)),
            ),
        )

    def _seeds(
        self,
        common: CommonExecutionRequest,
        round_number: int,
        client_id: str,
        local_epochs: int,
        branch: LoaderBranch,
    ) -> tuple[tuple[Seed, ...], tuple[Seed, ...], tuple[LoaderSeedRecord, ...]]:
        shuffle_namespace = (
            common.seed_derivation.personalized_dataloader_shuffle
            if branch is LoaderBranch.PERSONALIZED
            else common.seed_derivation.global_dataloader_shuffle
        )
        epoch_seeds: list[Seed] = []
        worker_seeds: list[Seed] = []
        evidence: list[LoaderSeedRecord] = []
        for local_epoch_index in range(local_epochs):
            components = (
                SeedComponent("training_seed", int(common.training_seed)),
                SeedComponent("round_number", round_number),
                SeedComponent("client_id", client_id),
                SeedComponent("local_epoch_index", local_epoch_index),
                SeedComponent("branch", branch.value),
            )
            epoch_seed = derive_execution_seed(
                shuffle_namespace,
                int(common.seed_derivation.digest_bytes),
                components,
            )
            worker_seed = derive_execution_seed(
                common.seed_derivation.worker_initialization,
                int(common.seed_derivation.digest_bytes),
                components,
            )
            epoch_seeds.append(epoch_seed)
            worker_seeds.append(worker_seed)
            evidence.append(
                LoaderSeedRecord(
                    round_number=round_number,
                    client_id=client_id,
                    local_epoch_index=local_epoch_index,
                    branch=branch,
                    shuffle_seed=epoch_seed,
                    worker_seed=worker_seed,
                )
            )
        return tuple(epoch_seeds), tuple(worker_seeds), tuple(evidence)

    def _aggregate_states(
        self,
        template: ModelState,
        weighted_states: tuple[tuple[int, ModelState], ...],
    ) -> ModelState:
        if not weighted_states or any(row_count < 1 for row_count, _ in weighted_states):
            raise LearningDataError("Federated aggregation requires positive client row counts")
        template_names = tuple(parameter.name for parameter in template.parameters)
        for _, state in weighted_states:
            if tuple(parameter.name for parameter in state.parameters) != template_names:
                raise LearningRuntimeError("Federated client states do not share an identical parameter order")
        flower_results = [
            (list(state_to_ndarrays(state)), row_count)
            for row_count, state in weighted_states
        ]
        aggregated_arrays = aggregate(flower_results)
        return ndarrays_to_state(template, tuple(aggregated_arrays))

    def _weighted_loss(
        self,
        model: torch.nn.Module,
        clients: tuple[ClientTensor, ...],
        common: CommonExecutionRequest,
    ) -> float:
        total_rows = sum(int(client.tensor.shape[0]) for client in clients)
        if total_rows < 1:
            raise LearningDataError("Calibration loss requires positive row counts")
        weighted_loss = 0.0
        for client in clients:
            row_count = int(client.tensor.shape[0])
            weighted_loss += row_count * reconstruction_loss(
                model,
                client.tensor,
                common.architecture,
                common.batching,
                common.runtime,
            )
        return weighted_loss / total_rows

    def _weighted_personalized_loss(
        self,
        states: tuple[ClientModelState, ...],
        clients: tuple[ClientTensor, ...],
        common: CommonExecutionRequest,
        initialization_seed: int,
    ) -> float:
        total_rows = sum(int(client.tensor.shape[0]) for client in clients)
        weighted_loss = 0.0
        for client in clients:
            model = build_autoencoder(
                common.architecture,
                int(client.tensor.shape[1]),
                initialization_seed,
                common.runtime,
            )
            load_model_state(model, self._client_state(states, client.client_id))
            row_count = int(client.tensor.shape[0])
            weighted_loss += row_count * reconstruction_loss(
                model,
                client.tensor,
                common.architecture,
                common.batching,
                common.runtime,
            )
        if total_rows < 1:
            raise LearningDataError("Personalized calibration loss requires positive row counts")
        return weighted_loss / total_rows

    @staticmethod
    def _client_state(states: tuple[ClientModelState, ...], client_id: str) -> ModelState:
        for state in states:
            if state.client_id == client_id:
                return state.state
        raise LearningDataError(f"Personalized state is unavailable for client '{client_id}'")

    @staticmethod
    def _input_dimension(clients: tuple[ClientTensor, ...]) -> int:
        if not clients:
            raise LearningDataError("Learning requires client tensors")
        return int(clients[0].tensor.shape[1])
