"""Thin model-training stage adapter."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.artifacts.store import ArtifactStore
from datp_core.core.identifiers import (
    CheckpointProfileId,
    DatasetId,
    ExperimentId,
    PopulationId,
    TrainingProfileId,
)
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.experiments import ExperimentRecord, PopulationRecord
from datp_core.learning.checkpoints.codec import (
    encode_global_checkpoints,
    encode_personalized_checkpoints,
)
from datp_core.learning.checkpoints.selection import CheckpointSelectionError, select_checkpoint_round
from datp_core.learning.contracts.checkpoints import (
    AuthorizedLookupSelection,
    CentralizedAlgorithmEvidence,
    CheckpointProfile,
    CheckpointSelectionEvidence,
    DittoAlgorithmEvidence,
    FedAvgAlgorithmEvidence,
    FedProxAlgorithmEvidence,
    LoaderSeedEvidence,
    RoundMetricEvidence,
)
from datp_core.learning.contracts.enums import LearningArtifactKind, TrainingAlgorithm
from datp_core.learning.contracts.model import (
    AdamOptimizerProfile,
    BatchingProfile,
    DenseAutoencoderProfile,
    LearningDataSchema,
)
from datp_core.learning.contracts.training import (
    CentralizedTrainingProfile,
    DittoTrainingProfile,
    FedAvgTrainingProfile,
    FedProxTrainingProfile,
    TrainingProfile,
)
from datp_core.core.seeding import Seed
from datp_core.learning.model.runtime import SeedDerivationProfile, TorchRuntimeProfile, create_runtime
from datp_core.learning.scoring.data import benign_client_tensors, read_materialization
from datp_core.learning.training.engine import (
    CentralizedExecutionRequest,
    CommonExecutionRequest,
    DittoExecutionRequest,
    FedAvgExecutionRequest,
    FederatedTrainingEngine,
    FedProxExecutionRequest,
    LearningError,
    TrainingResult,
)
from datp_core.pipeline.stages.context import TrainingContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


@dataclass(frozen=True, slots=True)
class ModelTrainingHandlerConfiguration:
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfile]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfile]
    model_architectures: TypedDomainRegistry[str, DenseAutoencoderProfile]
    optimizers: TypedDomainRegistry[str, AdamOptimizerProfile]
    batching_profiles: TypedDomainRegistry[str, BatchingProfile]
    learning_data_schemas: TypedDomainRegistry[str, LearningDataSchema]
    runtime_profile: TorchRuntimeProfile
    seed_derivation: SeedDerivationProfile


class ModelTrainingStageHandler:
    stage = StageKind.MODEL_TRAINING

    def __init__(
        self,
        config: ModelTrainingHandlerConfiguration,
        store: ArtifactStore,
        engine: FederatedTrainingEngine,
    ) -> None:
        self._config = config
        self._store = store
        self._engine = engine

    def execute(self, job: StageJob) -> StageJobOutcome:
        try:
            context = self._training_context(job)
            assert context.seed is not None
            profile, checkpoint_profile, architecture, optimizer, batching, data_schema = self._resolve(context)
            self._validate_outputs(job, profile)
            materialization_payload = self._store.read_bytes(job.input_path(LearningArtifactKind.MATERIALIZATION.value))
            materialization = read_materialization(
                materialization_payload,
                tuple(data_schema.feature_columns),
            )
            runtime = create_runtime(self._config.runtime_profile, architecture.precision)
            training_clients = benign_client_tensors(
                materialization,
                data_schema.split_profile.training,
                architecture.precision,
            )
            calibration_clients = benign_client_tensors(
                materialization,
                data_schema.split_profile.calibration,
                architecture.precision,
            )
            common = CommonExecutionRequest(
                architecture=architecture,
                optimizer=optimizer,
                batching=batching,
                checkpoint_rounds=tuple(int(value) for value in checkpoint_profile.capture_rounds),
                total_rounds=int(checkpoint_profile.total_rounds),
                training_seed=Seed(context.seed),
                seed_derivation=self._config.seed_derivation,
                runtime=runtime,
                training_clients=training_clients,
                calibration_clients=calibration_clients,
            )
            execution_request = self._execution_request(context, profile, common)
            result = self._engine.execute(execution_request)
            lookup_round = self._lookup_round(job, checkpoint_profile)
            selected_round = select_checkpoint_round(checkpoint_profile, result, lookup_round)
            evidence = self._evidence(result, selected_round, context)
            self._persist(job, result, evidence)
        except (CheckpointSelectionError, KeyError, LearningError, OSError, RuntimeError, TypeError, ValueError) as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )
        return StageJobOutcome.succeeded(
            node_key=job.node_key,
            stage=job.stage,
            produced_outputs=job.outputs,
        )

    def _resolve(
        self,
        context: TrainingContext,
    ) -> tuple[
        TrainingProfile,
        CheckpointProfile,
        DenseAutoencoderProfile,
        AdamOptimizerProfile,
        BatchingProfile,
        LearningDataSchema,
    ]:
        assert context.population_id is not None
        experiment = self._config.experiments.get(context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        checkpoint_profile = self._config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        optimizer = self._config.optimizers.get(profile.optimizer_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        population = self._config.populations.get(context.population_id)
        dataset = self._config.datasets.get(population.dataset_id)
        setup = dataset.setup(population.setup_id)
        materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
        learning_schema_id = getattr(materialization, "learning_schema_id", None)
        if learning_schema_id is None:
            raise TypeError("Materialization definition is missing learning_schema_id")
        data_schema = self._config.learning_data_schemas.get(learning_schema_id)
        return profile, checkpoint_profile, architecture, optimizer, batching, data_schema

    def _execution_request(
        self,
        context: TrainingContext,
        profile: TrainingProfile,
        common: CommonExecutionRequest,
    ) -> CentralizedExecutionRequest | FedAvgExecutionRequest | FedProxExecutionRequest | DittoExecutionRequest:
        match profile:
            case CentralizedTrainingProfile():
                self._reject_sweep_parameters(context)
                return CentralizedExecutionRequest(common=common, profile=profile)
            case FedAvgTrainingProfile():
                self._validate_full_participation(profile.participation.minimum_available_clients, common)
                self._reject_sweep_parameters(context)
                return FedAvgExecutionRequest(common=common, profile=profile)
            case FedProxTrainingProfile():
                self._validate_full_participation(profile.participation.minimum_available_clients, common)
                if context.federated_proximal_mu is None or context.ditto_proximal_weight is not None:
                    raise ValueError("FedProx requires exactly one resolved proximal coefficient")
                return FedProxExecutionRequest(
                    common=common,
                    profile=profile,
                    proximal_coefficient=context.federated_proximal_mu,
                )
            case DittoTrainingProfile():
                self._validate_full_participation(profile.participation.minimum_available_clients, common)
                if context.ditto_proximal_weight is None or context.federated_proximal_mu is not None:
                    raise ValueError("Ditto requires exactly one resolved personalization weight")
                return DittoExecutionRequest(
                    common=common,
                    profile=profile,
                    personalization_weight=context.ditto_proximal_weight,
                )
        raise TypeError("Unsupported resolved training profile")

    def _lookup_round(self, job: StageJob, checkpoint_profile: CheckpointProfile) -> int | None:
        if not isinstance(checkpoint_profile.selection, AuthorizedLookupSelection):
            return None
        payload = self._store.read_bytes(job.input_path(LearningArtifactKind.CHECKPOINT_SELECTION.value))
        evidence = CheckpointSelectionEvidence.model_validate_json(payload)
        if evidence.algorithm.algorithm is not checkpoint_profile.selection.required_algorithm:
            raise ValueError("Checkpoint lookup evidence was produced by an unauthorized algorithm")
        return int(evidence.selected_round)

    def _evidence(
        self,
        result: TrainingResult,
        selected_round: int,
        context: TrainingContext,
    ) -> CheckpointSelectionEvidence:
        match result.algorithm:
            case TrainingAlgorithm.CENTRALIZED:
                algorithm = CentralizedAlgorithmEvidence(algorithm=TrainingAlgorithm.CENTRALIZED)
            case TrainingAlgorithm.FEDAVG:
                algorithm = FedAvgAlgorithmEvidence(algorithm=TrainingAlgorithm.FEDAVG)
            case TrainingAlgorithm.FEDPROX:
                if context.federated_proximal_mu is None:
                    raise ValueError("FedProx evidence requires the resolved proximal coefficient")
                algorithm = FedProxAlgorithmEvidence(
                    algorithm=TrainingAlgorithm.FEDPROX,
                    proximal_coefficient=context.federated_proximal_mu,
                )
            case TrainingAlgorithm.DITTO:
                if context.ditto_proximal_weight is None:
                    raise ValueError("Ditto evidence requires the resolved personalization weight")
                algorithm = DittoAlgorithmEvidence(
                    algorithm=TrainingAlgorithm.DITTO,
                    personalization_weight=context.ditto_proximal_weight,
                )
            case _:
                raise ValueError("Unsupported training algorithm evidence")
        return CheckpointSelectionEvidence(
            schema_version=1,
            selected_round=selected_round,
            captured_rounds=tuple(checkpoint.round_number for checkpoint in result.global_checkpoints),
            round_metrics=tuple(
                RoundMetricEvidence(
                    round_number=metric.round_number,
                    global_calibration_loss=metric.global_calibration_loss,
                    personalized_calibration_loss=metric.personalized_calibration_loss,
                )
                for metric in result.round_metrics
            ),
            algorithm=algorithm,
            model_initialization_seed=result.model_initialization_seed,
            loader_seeds=tuple(
                LoaderSeedEvidence(
                    round_number=seed.round_number,
                    client_id=seed.client_id,
                    local_epoch_index=seed.local_epoch_index,
                    branch=seed.branch,
                    shuffle_seed=seed.shuffle_seed,
                    worker_seed=seed.worker_seed,
                )
                for seed in result.loader_seeds
            ),
        )

    def _persist(
        self,
        job: StageJob,
        result: TrainingResult,
        evidence: CheckpointSelectionEvidence,
    ) -> None:
        self._store.write_bytes_atomic(
            job.output_path(LearningArtifactKind.CHECKPOINT.value),
            encode_global_checkpoints(result.global_checkpoints),
        )
        if result.algorithm is TrainingAlgorithm.DITTO:
            self._store.write_bytes_atomic(
                job.output_path(LearningArtifactKind.PERSONALIZED_CHECKPOINT.value),
                encode_personalized_checkpoints(result.personalized_checkpoints),
            )
        self._store.write_bytes_atomic(
            job.output_path(LearningArtifactKind.SELECTION_EVIDENCE.value),
            evidence.model_dump_json(exclude_none=False).encode("utf-8"),
        )

    @staticmethod
    def _training_context(job: StageJob) -> TrainingContext:
        if not isinstance(job.context, TrainingContext):
            raise TypeError("Model training requires TrainingContext")
        if job.context.population_id is None:
            raise ValueError("Model training requires an explicitly resolved population identifier")
        if job.context.seed is None:
            raise ValueError("Model training requires an explicitly resolved training seed")
        return job.context

    @staticmethod
    def _reject_sweep_parameters(context: TrainingContext) -> None:
        if context.federated_proximal_mu is not None or context.ditto_proximal_weight is not None:
            raise ValueError("Resolved sweep parameters are forbidden for this training algorithm")

    @staticmethod
    def _validate_full_participation(minimum_available_clients: int, common: CommonExecutionRequest) -> None:
        if len(common.training_clients) < int(minimum_available_clients):
            raise ValueError("Resolved population does not satisfy the configured client minimum")

    @staticmethod
    def _validate_outputs(job: StageJob, profile: TrainingProfile) -> None:
        actual = {output.name for output in job.outputs}
        required = {
            LearningArtifactKind.CHECKPOINT.value,
            LearningArtifactKind.SELECTION_EVIDENCE.value,
        }
        if isinstance(profile, DittoTrainingProfile):
            required.add(LearningArtifactKind.PERSONALIZED_CHECKPOINT.value)
        if actual != required:
            raise ValueError("Model-training outputs do not match the resolved algorithm contract")
