"""Operating-point evaluation stage handler."""

from __future__ import annotations

from io import BytesIO

import pandera.errors as pandera_errors
import polars as pl

from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_test_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.evaluation.operating_points import evaluate_operating_points
from datp_core.pipeline.stages.context import EvaluationContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class OperatingPointEvaluationStageHandler:
    stage = StageKind.OPERATING_POINT_EVALUATION

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        if not isinstance(job.context, EvaluationContext):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Operating-point evaluation requires an EvaluationContext",
            )

        ctx: EvaluationContext = job.context

        try:
            thresholds = validate_threshold_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("thresholds"))))
            )
            scores = validate_test_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("test_scores"))))
            )

            metrics = evaluate_operating_points(
                scores=scores,
                thresholds=thresholds,
                missing_threshold_policy=ctx.missing_threshold_policy,
            )

            if ctx.threshold_policy_id is not None:
                metrics = metrics.with_columns(
                    pl.lit(ctx.threshold_policy_id.value).alias("policy_id"),
                )
            metrics = metrics.with_columns(
                pl.lit(ctx.seed).alias("seed"),
            )

            validate_client_metric_frame(metrics)

            payload = BytesIO()
            metrics.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("client_metrics"), payload.getvalue())

        except (OSError, ValueError, pandera_errors.SchemaError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))

        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
