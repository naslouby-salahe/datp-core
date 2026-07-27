"""Thin stage adapters: calibration subsampling and threshold construction."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ClientId
from datp_core.pipeline.stages.context import EvaluationContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.thresholding.calibration import subsample_calibration_scores
from datp_core.thresholding.engine import ThresholdEngine
from datp_core.thresholding.models import (
    CalibrationSampleRequest,
    EmptyCalibrationError,
    FamilyAssignments,
    InsufficientCalibrationError,
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
        subset = experiment.calibration_subset
        if subset is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Calibration subsampling is not configured for this experiment",
            )

        namespace = self._config.protocol_determinism.seed_namespaces["calibration_subsample"]
        digest_bytes = int(self._config.protocol_determinism.derived_seed_algorithm["digest_bytes"])

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
        except (KeyError, OSError, ValueError, InsufficientCalibrationError) as exc:
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
        if ctx.threshold_policy_id is None or ctx.population_id is None or ctx.seed is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=("Threshold construction requires policy, population, and seed"),
            )

        policy = self._config.threshold_policies.get(ctx.threshold_policy_id)
        if policy is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=f"Unknown threshold policy: {ctx.threshold_policy_id.value}",
            )

        population = self._config.populations.get(ctx.population_id)
        dataset = self._config.datasets[population.dataset_id]

        try:
            scores = validate_calibration_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("calibration_scores"))))
            )
            if scores.is_empty():
                raise EmptyCalibrationError("Calibration score frame is empty — cannot construct thresholds")

            family_assignments = None
            if dataset.field_schema.label_fields.family_map:
                family_assignments = FamilyAssignments(
                    mapping=tuple(
                        (ClientId(k), v) for k, v in dict(dataset.field_schema.label_fields.family_map).items()
                    )
                )
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
            payload = BytesIO()
            frame.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("thresholds"), payload.getvalue())
            self._store.write_bytes_atomic(job.output_path("diagnostics"), diagnostics)
        except (OSError, ThresholdingError) as exc:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=str(exc),
            )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
