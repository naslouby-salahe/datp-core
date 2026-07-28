"""Pipeline stage for federated model training (FedAvg/FedProx/Ditto)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import torch
from safetensors.torch import save as save_safetensors

from datp_core.artifacts.store import ArtifactStore
from datp_core.config.resolution.protocols.training import ProtocolDeterminismRecord
from datp_core.config.resolution.runtime import ResolvedRuntimeConfiguration
from datp_core.core.identifiers import (
    CheckpointProfileId,
    DatasetId,
    ExperimentId,
    PopulationId,
    TrainingProfileId,
)
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.contracts.enums import SplitMembership, SplitMethod
from datp_core.experiments import ExperimentRecord, PopulationRecord
from datp_core.learning.checkpoints.selection import (
    select_anchor_checkpoint_round,
    select_lowest_validation_loss_checkpoint,
)
from datp_core.learning.contracts.architecture import ModelArchitectureRecord
from datp_core.learning.contracts.checkpoints import CheckpointProfileRecord
from datp_core.learning.contracts.enums import (
    DevicePolicy,
    PersonalizationStrategy,
    TrainingParticipation,
    TrainingProfileKind,
)
from datp_core.learning.contracts.optimization import BatchingRecord, OptimizerRecord
from datp_core.learning.contracts.training import TrainingProfileRecord
from datp_core.learning.model.autoencoder import DynamicDenseAutoencoder
from datp_core.learning.model.determinism import derive_model_initialization_seed, set_deterministic_seeds
from datp_core.learning.model.device import require_cuda_training_device
from datp_core.learning.scoring.data import load_benign_client_tensors, materialized_feature_columns
from datp_core.learning.training.federated import federated_train_autoencoder
from datp_core.learning.training.models import DataloaderShuffleSeed, DittoTrainingResult, FederatedTrainingResult
from datp_core.learning.training.personalization import ditto_train_autoencoder
from datp_core.pipeline.stages.context import TrainingContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


@dataclass(frozen=True, slots=True)
class ModelTrainingHandlerConfiguration:
    """Narrow configuration for ModelTrainingStageHandler — only the registries it needs."""

    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    model_architectures: TypedDomainRegistry[str, ModelArchitectureRecord]
    optimizers: TypedDomainRegistry[str, OptimizerRecord]
    batching_profiles: TypedDomainRegistry[str, BatchingRecord]
    runtime: ResolvedRuntimeConfiguration
    protocol_determinism: ProtocolDeterminismRecord


class ModelTrainingStageHandler:
    """Train one configured full-participation federated model and persist its checkpoint grid."""

    stage = StageKind.MODEL_TRAINING

    def __init__(self, config: ModelTrainingHandlerConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def _unpack_training_result(
        self, result: FederatedTrainingResult | DittoTrainingResult, is_ditto: bool
    ) -> tuple[
        tuple[tuple[int, float], ...],
        tuple[tuple[int, float], ...] | None,
        tuple[int, ...],
        tuple[DataloaderShuffleSeed, ...],
        dict[str, torch.Tensor],
    ]:
        if is_ditto:
            assert isinstance(result, DittoTrainingResult)
            ditto_result = result
            round_losses = ditto_result.global_round_losses
            personalized_round_losses = ditto_result.personalized_round_losses
            scheduled_rounds = tuple(checkpoint.round_number for checkpoint in ditto_result.scheduled_checkpoints)
            derived_shuffle_seeds = ditto_result.derived_shuffle_seeds
            checkpoint_grid = {
                f"round_{checkpoint.round_number}.{name}": tensor
                for checkpoint in ditto_result.scheduled_checkpoints
                for name, tensor in checkpoint.global_state
            }
        else:
            assert isinstance(result, FederatedTrainingResult)
            federated_result = result
            round_losses = federated_result.round_losses
            personalized_round_losses = None
            scheduled_rounds = tuple(checkpoint.round_number for checkpoint in federated_result.scheduled_checkpoints)
            derived_shuffle_seeds = federated_result.derived_shuffle_seeds
            checkpoint_grid = {
                f"round_{checkpoint.round_number}.{name}": tensor
                for checkpoint in federated_result.scheduled_checkpoints
                for name, tensor in checkpoint.state
            }
        return round_losses, personalized_round_losses, scheduled_rounds, derived_shuffle_seeds, checkpoint_grid

    def _select_checkpoint_round(
        self,
        checkpoint_profile: CheckpointProfileRecord,
        round_losses: tuple[tuple[int, float], ...],
        scheduled_rounds: tuple[int, ...],
    ) -> int:
        if checkpoint_profile.convergence is not None:
            assert checkpoint_profile.total_rounds is not None
            return select_anchor_checkpoint_round(
                convergence=checkpoint_profile.convergence,
                recorded_losses=round_losses,
                round_cap=int(checkpoint_profile.total_rounds.value),
            )
        return select_lowest_validation_loss_checkpoint(
            scheduled_rounds=tuple(int(value.value) for value in checkpoint_profile.selected_rounds),
            recorded_losses=round_losses,
        )

    def _persist_training_outputs(
        self,
        job: StageJob,
        result: FederatedTrainingResult | DittoTrainingResult,
        is_ditto: bool,
        checkpoint_grid: dict[str, torch.Tensor],
        selection_payload: bytes,
    ) -> StageJobOutcome:
        try:
            self._store.write_bytes_atomic(job.output_path("checkpoint"), save_safetensors(checkpoint_grid))
            if is_ditto:
                assert isinstance(result, DittoTrainingResult)
                ditto_result = result
                personalized_grid = {
                    f"round_{checkpoint.round_number}.client_{client_id}.{name}": tensor
                    for checkpoint in ditto_result.scheduled_checkpoints
                    for client_id, state in checkpoint.personalized_states
                    for name, tensor in state
                }
                self._store.write_bytes_atomic(
                    job.output_path("personalized_checkpoint"), save_safetensors(personalized_grid)
                )
            self._store.write_bytes_atomic(job.output_path("selection_evidence"), selection_payload)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)

    def _check_profile_parameter_errors(
        self,
        profile: TrainingProfileRecord,
        proximal_mu: float | None,
        ditto_weight: float | None,
        is_ditto: bool,
        job: StageJob,
    ) -> StageJobOutcome | None:
        if profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
            if proximal_mu is None or proximal_mu <= 0.0 or ditto_weight is not None:
                return StageJobOutcome.failed(
                    node_key=job.node_key,
                    stage=job.stage,
                    error_message="FedProx training requires a positive sweep-resolved mu",
                )
        elif is_ditto:
            if (
                proximal_mu is not None
                or ditto_weight is None
                or ditto_weight <= 0.0
                or profile.personalized_local_epochs is None
            ):
                return StageJobOutcome.failed(
                    node_key=job.node_key,
                    stage=job.stage,
                    error_message="Ditto training requires a positive sweep-resolved personalization weight",
                )
        elif proximal_mu is not None or ditto_weight is not None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="FedAvg training must not carry a FedProx coefficient",
            )
        return None

    def execute(self, job: StageJob) -> StageJobOutcome:
        assert isinstance(job.context, TrainingContext)
        ctx = job.context
        experiment = self._config.experiments.get(ctx.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        if (
            profile.kind
            not in {TrainingProfileKind.FEDERATED_AVERAGING_TRAINING, TrainingProfileKind.FEDERATED_PROX_TRAINING}
            or profile.participation != TrainingParticipation.FULL
        ):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Training profile '{profile.identifier.value}' is not implemented by the FedAvg stage",
            )
        if ctx.seed is None or profile.local_epochs is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Training requires a seed and local epochs"
            )
        proximal_mu = ctx.federated_proximal_mu
        ditto_weight = ctx.ditto_proximal_weight
        is_ditto = profile.personalization == PersonalizationStrategy.DITTO

        error = self._check_profile_parameter_errors(profile, proximal_mu, ditto_weight, is_ditto, job)
        if error is not None:
            return error

        population = self._config.populations.get(ctx.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        setup = dataset.setup(population.setup_id)
        materialization_config = next(
            item for item in dataset.materializations if item.identifier == setup.materialization_id
        )
        checkpoint_profile = self._config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
        if checkpoint_profile.total_rounds is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Checkpoint profile has no round budget"
            )
        try:
            materialization_bytes = self._store.read_bytes(job.input_path("materialization"))
        except (OSError, ValueError):
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Materialization artifact is unavailable"
            )
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        optimizer = self._config.optimizers.get(profile.optimizer_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            with TemporaryDirectory(prefix="datp_training_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization_bytes)
                training_split = (
                    SplitMembership.HISTORICAL_TRAINING.value
                    if materialization_config.split.method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL
                    else SplitMembership.TRAIN.value
                )
                calibration_split = (
                    SplitMembership.HISTORICAL_CALIBRATION.value if training_split == SplitMembership.HISTORICAL_TRAINING.value else SplitMembership.CALIBRATION.value
                )
                feature_columns = materialized_feature_columns(materialized_path)
                training_clients = load_benign_client_tensors(materialized_path, training_split, feature_columns)
                calibration_clients = load_benign_client_tensors(materialized_path, calibration_split, feature_columns)
                if self._config.runtime.active_execution_profile.device_policy != DevicePolicy.CUDA_REQUIRED:
                    raise ValueError("Model training requires the configured CUDA-required execution profile")
                initialization_namespace = self._config.protocol_determinism.seed_namespaces["model_initialization"]
                shuffle_namespace = self._config.protocol_determinism.seed_namespaces["dataloader_shuffle"]
                digest_bytes = self._config.protocol_determinism.derived_seed_digest_bytes
                initialization_seed = derive_model_initialization_seed(
                    key=initialization_namespace.key,
                    digest_bytes=int(digest_bytes),
                    training_seed=ctx.seed,
                )
                set_deterministic_seeds(initialization_seed)
                model = DynamicDenseAutoencoder(
                    len(feature_columns), tuple(int(value.value) for value in architecture.hidden_dims)
                )
                training_kwargs = {
                    "rounds": int(checkpoint_profile.total_rounds.value),
                    "local_epochs": int(profile.local_epochs.value),
                    "learning_rate": float(optimizer.learning_rate.value),
                    "batch_size": int(batching.micro_batch_size.value),
                    "seed": ctx.seed,
                    "device": require_cuda_training_device(),
                    "beta_1": optimizer.beta_1,
                    "beta_2": optimizer.beta_2,
                    "epsilon": float(optimizer.epsilon.value),
                    "weight_decay": float(optimizer.weight_decay.value),
                    "amsgrad": optimizer.amsgrad,
                    "shuffle_each_epoch": batching.shuffle_each_epoch,
                    "checkpoint_rounds": tuple(int(value.value) for value in checkpoint_profile.selected_rounds),
                    "shuffle_seed_key": shuffle_namespace.key,
                    "shuffle_seed_digest_bytes": digest_bytes,
                }
                if is_ditto:
                    assert profile.personalized_local_epochs is not None
                    assert ditto_weight is not None
                    result = ditto_train_autoencoder(
                        model,
                        training_clients,
                        calibration_clients,
                        personalized_local_epochs=int(profile.personalized_local_epochs.value),
                        proximal_weight=ditto_weight,
                        **training_kwargs,
                    )
                else:
                    result = federated_train_autoencoder(
                        model, training_clients, calibration_clients, proximal_mu=proximal_mu, **training_kwargs
                    )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        round_output = self._unpack_training_result(result, is_ditto)
        round_losses, personalized_round_losses, scheduled_rounds, derived_shuffle_seeds, checkpoint_grid = round_output
        selected_round = self._select_checkpoint_round(checkpoint_profile, round_losses, scheduled_rounds)
        if selected_round not in scheduled_rounds:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Selected checkpoint state was not captured"
            )
        selection_payload = json.dumps(
            {
                "schema_version": 1,
                "selected_round": selected_round,
                "checkpoint_rounds": scheduled_rounds,
                "round_losses": round_losses,
                "personalized_round_losses": personalized_round_losses,
                "federated_proximal_mu": proximal_mu,
                "ditto_proximal_weight": ditto_weight,
                "model_initialization_seed": initialization_seed,
                "dataloader_shuffle_seeds": [
                    [seed.round_number, seed.client_id, seed.local_epoch, seed.value] for seed in derived_shuffle_seeds
                ],
            },
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return self._persist_training_outputs(job, result, is_ditto, checkpoint_grid, selection_payload)
