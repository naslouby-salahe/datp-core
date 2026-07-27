"""Score one explicitly supplied materialization/checkpoint pair."""

from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import polars as pl

from datp_core.artifacts.schemas.scores import validate_calibration_score_frame, validate_test_score_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.resolution.runtime import ResolvedRuntimeConfiguration
from datp_core.core.identifiers import DatasetId, ExperimentId, PopulationId, TrainingProfileId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts import ResolvedDataset
from datp_core.data.contracts.enums import SplitMembership, SplitMethod
from datp_core.experiments import ExperimentRecord, PopulationRecord
from datp_core.learning.contracts.architecture import ModelArchitectureRecord
from datp_core.learning.contracts.enums import (
    CheckpointAuthorization,
    DevicePolicy,
    PersonalizationStrategy,
    ScoreOrientation,
)
from datp_core.learning.contracts.optimization import BatchingRecord
from datp_core.learning.contracts.training import TrainingProfileRecord
from datp_core.learning.model.device import require_cuda_training_device
from datp_core.learning.scoring.checkpoints import (
    build_model_from_checkpoint_bytes,
    build_personalized_models_from_bytes,
)
from datp_core.learning.scoring.compute import (
    score_materialized_split,
    score_personalized_materialized_split,
)
from datp_core.learning.scoring.data import materialized_feature_columns
from datp_core.pipeline.stages.context import TrainingContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome

_CALIBRATION_SCORES = "calibration_scores"
_FUTURE_RECALIBRATION_SCORES = "future_recalibration_scores"
_TEST_SCORES = "test_scores"
_CHECKPOINT_SELECTION = "checkpoint_selection"


@dataclass(frozen=True, slots=True)
class ScoreGenerationHandlerConfiguration:
    """Narrow configuration for ScoreGenerationStageHandler — only the registries it needs."""

    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    model_architectures: TypedDomainRegistry[str, ModelArchitectureRecord]
    batching_profiles: TypedDomainRegistry[str, BatchingRecord]
    runtime: ResolvedRuntimeConfiguration


def _score_split(
    output_name: str,
    context: TrainingContext,
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord],
    populations: TypedDomainRegistry[PopulationId, PopulationRecord],
    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset],
) -> str | None:
    experiment = experiments.get(context.experiment_id)
    population = populations.get(context.population_id or experiment.population_ids[0])
    dataset = datasets.get(population.dataset_id)
    setup = dataset.setup(population.setup_id)
    materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
    temporal = materialization.split_method is SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL
    if output_name == _CALIBRATION_SCORES:
        return SplitMembership.HISTORICAL_CALIBRATION.value if temporal else SplitMembership.CALIBRATION.value
    if output_name == _FUTURE_RECALIBRATION_SCORES:
        return SplitMembership.FUTURE_RECALIBRATION.value if temporal else None
    if output_name == _TEST_SCORES:
        return SplitMembership.FUTURE_EVALUATION.value if temporal else SplitMembership.TEST.value
    return None


class ScoreGenerationStageHandler:
    stage = StageKind.SCORE_GENERATION

    def __init__(self, config: ScoreGenerationHandlerConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        assert isinstance(job.context, TrainingContext)
        ctx = job.context
        output_name = job.outputs[0].name
        split = _score_split(
            output_name, ctx, self._config.experiments, self._config.populations, self._config.datasets
        )
        if split is None:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message="Unknown score output")
        experiment = self._config.experiments.get(ctx.experiment_id)
        profile = self._config.training_profiles.get(experiment.training_profile_id)
        try:
            selection_path = job.input_path("selection_evidence")
            if profile.checkpoint_authorization is CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE and any(
                item.name == _CHECKPOINT_SELECTION for item in job.inputs
            ):
                selection_path = job.input_path("checkpoint_selection")
            selection = json.loads(self._store.read_bytes(selection_path))
            selected_round = selection.get("selected_round") if isinstance(selection, dict) else None
            if not isinstance(selected_round, int):
                raise ValueError("Selected-checkpoint evidence is malformed")
            checkpoint = self._store.read_bytes(job.input_path("checkpoint"))
            materialization = self._store.read_bytes(job.input_path("materialization"))
            personalized = (
                self._store.read_bytes(job.input_path("personalized_checkpoint"))
                if profile.personalization is PersonalizationStrategy.DITTO
                else None
            )
        except (KeyError, OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        population = self._config.populations.get(ctx.population_id or experiment.population_ids[0])
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        architecture = self._config.model_architectures.get(profile.model_architecture_id)
        batching = self._config.batching_profiles.get(profile.batching_profile_id)
        try:
            if self._config.runtime.active_execution_profile.device_policy != DevicePolicy.CUDA_REQUIRED:
                raise ValueError("Score generation requires the configured CUDA-required execution profile")
            with TemporaryDirectory(prefix="datp_scoring_") as temporary_directory:
                materialized_path = Path(temporary_directory) / "materialized.parquet"
                materialized_path.write_bytes(materialization)
                features = dataset.field_schema.model_features
                feature_columns = (
                    features.order if features is not None else materialized_feature_columns(materialized_path)
                )
                if personalized is not None:
                    client_ids = (
                        pl.read_parquet(materialized_path, columns=["client_id"])["client_id"].unique().sort().to_list()
                    )
                    models = build_personalized_models_from_bytes(
                        personalized,
                        selected_round,
                        client_ids,
                        len(feature_columns),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_personalized_materialized_split(
                        models,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
                else:
                    model = build_model_from_checkpoint_bytes(
                        checkpoint,
                        selected_round,
                        len(feature_columns),
                        tuple(int(value.value) for value in architecture.hidden_dims),
                    )
                    scores = score_materialized_split(
                        model,
                        materialized_path,
                        split=split,
                        feature_columns=feature_columns,
                        batch_size=int(batching.micro_batch_size.value),
                        device=require_cuda_training_device(),
                    )
        except (OSError, RuntimeError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        scores = scores.with_columns(
            pl.lit(job.input_path("checkpoint")).alias("checkpoint_path"),
            pl.lit(ctx.seed).alias("seed"),
            pl.lit(ScoreOrientation.HIGHER_MORE_ANOMALOUS.value).alias("score_orientation"),
        )
        try:
            validated = (
                validate_test_score_frame(scores)
                if output_name == _TEST_SCORES
                else validate_calibration_score_frame(scores)
            )
            payload = BytesIO()
            validated.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path(output_name), payload.getvalue())
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
