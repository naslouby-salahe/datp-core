"""Thin stage adapters: calibration subsampling and threshold construction."""

from __future__ import annotations

import json
from io import BytesIO

import polars as pl
from pandera.errors import SchemaError, SchemaErrors

from datp_core.artifacts.errors import ArtifactStoreError
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.stages.context import EvaluationContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.thresholding.calibration import subsample_calibration_scores
from datp_core.thresholding.engine import ThresholdEngine
from datp_core.thresholding.models import (
    CalibrationSampleRequest,
    EmptyCalibrationError,
    InsufficientCalibrationError,
    ThresholdConfigurationError,
    ThresholdConstructionRequest,
    ThresholdingError,
)
from datp_core.thresholding.serialization import (
    calibration_to_benign_scores,
    diagnostics_to_json,
    threshold_set_to_frame,
)


class CalibrationSubsamplingStageHandler:
    """Stage handler for deterministic calibration subsampling."""

    stage = StageKind.CALIBRATION_SUBSAMPLING

    def __init__(self, config: ResolvedProjectConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        ctx = job.context
        if not isinstance(ctx, EvaluationContext):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Expected EvaluationContext, got {type(ctx).__name__}",
            )
        if ctx.seed is None or ctx.calibration_sample_count is None or ctx.calibration_replicate is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=("Calibration subsampling requires a seed, sample count, and replicate"),
            )

        experiment = self._config.experiments.get(ctx.experiment_id)
        if experiment is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Unknown experiment: {ctx.experiment_id}",
            )
        subset = experiment.calibration_subset
        if subset is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Calibration subsampling is not configured for this experiment",
            )

        namespace = self._config.protocol_determinism.calibration_subsample_namespace
        digest_bytes = int(self._config.protocol_determinism.derived_seed_digest_bytes)

        try:
            scores = validate_calibration_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("calibration_scores"))))
            )
            request = CalibrationSampleRequest(
                requested_sample_count=ctx.calibration_sample_count,
                training_seed=ctx.seed,
                selection_seed=subset.selection_seed.value,
                replicate=ctx.calibration_replicate,
                namespace_key=namespace.key,
                digest_bytes=digest_bytes,
            )
            sampled = subsample_calibration_scores(scores, request=request)
            payload = BytesIO()
            validate_calibration_score_frame(sampled).write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("calibration_subset_scores"), payload.getvalue())
        except (
            OSError,
            InsufficientCalibrationError,
            ThresholdConfigurationError,
            SchemaError,
            SchemaErrors,
            ArtifactStoreError,
        ) as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)


class ThresholdConstructionStageHandler:
    """Stage handler for threshold construction from calibration scores."""

    stage = StageKind.THRESHOLD_CONSTRUCTION

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        store: ArtifactStore,
        engine: ThresholdEngine,
    ) -> None:
        self._config = config
        self._store = store
        self._engine = engine

    def execute(self, job: StageJob) -> StageJobOutcome:
        ctx = job.context
        if not isinstance(ctx, EvaluationContext):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Expected EvaluationContext, got {type(ctx).__name__}",
            )
        if ctx.population_id is None or ctx.seed is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=("Threshold construction requires population and seed"),
            )

        policy = self._config.threshold_policies.get(ctx.threshold_policy_id)
        if policy is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Unknown threshold policy: {ctx.threshold_policy_id.value}",
            )

        population = self._config.populations.get(ctx.population_id)
        if population is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Unknown population: {ctx.population_id.value}",
            )
        dataset = self._config.datasets.get(population.dataset_id)
        if dataset is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Unknown dataset: {population.dataset_id}",
            )

        if self._config.experiments.get(ctx.experiment_id) is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Unknown experiment: {ctx.experiment_id}",
            )

        try:
            scores = validate_calibration_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("calibration_scores"))))
            )
            if scores.is_empty():
                raise EmptyCalibrationError("Calibration score frame is empty — cannot construct thresholds")

            family_assignments = dataset.family_assignments
            request = ThresholdConstructionRequest(
                policy_id=ctx.threshold_policy_id,
                policy=policy,
                calibration=calibration_to_benign_scores(scores, ctx.population_id),
                population_id=ctx.population_id,
                family_assignments=family_assignments,
            )
            threshold_set = self._engine.construct(request)
            frame = threshold_set_to_frame(threshold_set)
            diagnostics = diagnostics_to_json(threshold_set.diagnostics)

            validate_threshold_frame(frame)
            buffer = BytesIO()
            frame.write_parquet(buffer)
            thresholds_payload = buffer.getvalue()

            thresholds_path = job.output_path("thresholds")
            diagnostics_path = job.output_path("diagnostics")
            json.loads(diagnostics)  # validate well-formed JSON before publication

            self._store.write_bytes_batch(
                {
                    thresholds_path: thresholds_payload,
                    diagnostics_path: diagnostics,
                },
            )
        except (OSError, ThresholdingError) as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
