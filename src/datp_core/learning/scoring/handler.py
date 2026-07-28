"""Thin reconstruction-score generation stage adapter."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import polars as pl

from datp_core.artifacts.schemas.scores import validate_calibration_score_frame, validate_test_score_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.core.identifiers import DatasetId, ExperimentId, PopulationId, TrainingProfileId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.contracts.enums import SplitMembership
from datp_core.experiments import ExperimentRecord, PopulationRecord
from datp_core.learning.contracts.checkpoints import CheckpointSelectionEvidence
from datp_core.learning.contracts.enums import (
    CheckpointAuthorization,
    LearningArtifactKind,
    ScoreArtifactKind,
    ScoreOrientation,
)
from datp_core.learning.contracts.model import (
    BatchingProfile,
    DenseAutoencoderProfile,
    LearningDataSchema,
    StandardSplitProfile,
    TemporalSplitProfile,
)
from datp_core.learning.contracts.training import DittoTrainingProfile, TrainingProfile
from datp_core.learning.model.runtime import TorchRuntimeProfile, create_runtime
from datp_core.learning.scoring.data import read_materialization
from datp_core.learning.scoring.service import (
    GlobalScoringRequest,
    PersonalizedScoringRequest,
    ReconstructionScoringService,
)
from datp_core.pipeline.stages.context import TrainingContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


@dataclass(frozen=True, slots=True)
class ScoreGenerationHandlerConfiguration:
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfile]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    model_architectures: TypedDomainRegistry[str, DenseAutoencoderProfile]
    batching_profiles: TypedDomainRegistry[str, BatchingProfile]
    learning_data_schemas: TypedDomainRegistry[str, LearningDataSchema]
    runtime_profile: TorchRuntimeProfile


class ScoreGenerationStageHandler:
    stage = StageKind.SCORE_GENERATION

    def __init__(
        self,
        config: ScoreGenerationHandlerConfiguration,
        store: ArtifactStore,
        service: ReconstructionScoringService,
    ) -> None:
        self._config = config
        self._store = store
        self._service = service

    def execute(self, job: StageJob) -> StageJobOutcome:
        try:
            context = self._training_context(job)
            output_kind = self._output_kind(job)
            profile, architecture, batching, data_schema = self._resolve(context)
            split = self._split(output_kind, data_schema)
            selection = self._selection_evidence(job, profile)
            materialization = read_materialization(
                self._store.read_bytes(job.input_path(LearningArtifactKind.MATERIALIZATION.value)),
                tuple(data_schema.feature_columns),
            )
            runtime = create_runtime(self._config.runtime_profile, architecture.precision)
            if isinstance(profile, DittoTrainingProfile):
                request = PersonalizedScoringRequest(
                    materialization=materialization,
                    split=split,
                    personalized_checkpoint_payload=self._store.read_bytes(
                        job.input_path(LearningArtifactKind.PERSONALIZED_CHECKPOINT.value)
                    ),
                    selected_round=int(selection.selected_round),
                    architecture=architecture,
                    batching=batching,
                    runtime=runtime,
                    model_initialization_seed=int(selection.model_initialization_seed),
                )
            else:
                request = GlobalScoringRequest(
                    materialization=materialization,
                    split=split,
                    checkpoint_payload=self._store.read_bytes(
                        job.input_path(LearningArtifactKind.CHECKPOINT.value)
                    ),
                    selected_round=int(selection.selected_round),
                    architecture=architecture,
                    batching=batching,
                    runtime=runtime,
                    model_initialization_seed=int(selection.model_initialization_seed),
                )
            scores = self._service.score(request).with_columns(
                pl.lit(job.input_path(LearningArtifactKind.CHECKPOINT.value)).alias("checkpoint_path"),
                pl.lit(int(context.seed)).alias("seed"),
                pl.lit(ScoreOrientation.HIGHER_MORE_ANOMALOUS.value).alias("score_orientation"),
            )
            validated = (
                validate_test_score_frame(scores)
                if output_kind is ScoreArtifactKind.TEST_SCORES
                else validate_calibration_score_frame(scores)
            )
            payload = BytesIO()
            validated.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path(output_kind.value), payload.getvalue())
        except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
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
    ) -> tuple[TrainingProfile, DenseAutoencoderProfile, BatchingProfile, LearningDataSchema]:
        experiment = self._config.experiments.get(context.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        population = self._config.populations.get(context.population_id)
        dataset = self._config.datasets.get(population.dataset_id)
        setup = dataset.setup(population.setup_id)
        materialization = next(
            item for item in dataset.materializations if item.identifier == setup.materialization_id
        )
        data_schema = self._config.learning_data_schemas.get(materialization.learning_schema_id)
        return profile, architecture, batching, data_schema

    def _selection_evidence(
        self,
        job: StageJob,
        profile: TrainingProfile,
    ) -> CheckpointSelectionEvidence:
        input_kind = (
            LearningArtifactKind.CHECKPOINT_SELECTION
            if profile.checkpoint_authorization is CheckpointAuthorization.PRIMARY_SELECTION
            else LearningArtifactKind.SELECTION_EVIDENCE
        )
        return CheckpointSelectionEvidence.model_validate_json(
            self._store.read_bytes(job.input_path(input_kind.value))
        )

    @staticmethod
    def _split(output_kind: ScoreArtifactKind, data_schema: LearningDataSchema) -> SplitMembership:
        profile = data_schema.split_profile
        match profile:
            case StandardSplitProfile():
                match output_kind:
                    case ScoreArtifactKind.CALIBRATION_SCORES:
                        return profile.calibration
                    case ScoreArtifactKind.TEST_SCORES:
                        return profile.test
                    case ScoreArtifactKind.FUTURE_RECALIBRATION_SCORES:
                        raise ValueError("Standard split profile has no future recalibration split")
            case TemporalSplitProfile():
                match output_kind:
                    case ScoreArtifactKind.CALIBRATION_SCORES:
                        return profile.calibration
                    case ScoreArtifactKind.FUTURE_RECALIBRATION_SCORES:
                        return profile.future_recalibration
                    case ScoreArtifactKind.TEST_SCORES:
                        return profile.test
        raise ValueError("Score artifact kind has no split binding")

    @staticmethod
    def _training_context(job: StageJob) -> TrainingContext:
        if not isinstance(job.context, TrainingContext):
            raise TypeError("Score generation requires TrainingContext")
        if job.context.population_id is None:
            raise ValueError("Score generation requires an explicitly resolved population identifier")
        if job.context.seed is None:
            raise ValueError("Score generation requires an explicitly resolved training seed")
        return job.context

    @staticmethod
    def _output_kind(job: StageJob) -> ScoreArtifactKind:
        if len(job.outputs) != 1:
            raise ValueError("Score generation requires exactly one declared output")
        (output,) = job.outputs
        return ScoreArtifactKind(output.name)
