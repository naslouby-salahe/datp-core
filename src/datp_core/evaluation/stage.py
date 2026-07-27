"""Operating-point evaluation stage handler."""

from __future__ import annotations

import pandera.errors as pandera_errors
import polars as pl

from datp_core.artifacts.schemas.metrics import (
    validate_client_metric_frame,
)
from datp_core.artifacts.schemas.scores import (
    validate_test_score_frame,
)
from datp_core.artifacts.schemas.thresholds import (
    validate_threshold_frame,
)
from datp_core.artifacts.store import ArtifactStore
from datp_core.evaluation.enums import (
    EvaluationArtifactKey,
    EvaluationColumn,
)
from datp_core.evaluation.operating_points import (
    evaluate_operating_points,
)
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
                error_message=("Operating-point evaluation requires an EvaluationContext"),
            )

        context = job.context

        try:
            thresholds = validate_threshold_frame(
                self._store.read_parquet(job.input_path(EvaluationArtifactKey.THRESHOLDS))
            )

            scores = validate_test_score_frame(
                self._store.read_parquet(job.input_path(EvaluationArtifactKey.TEST_SCORES))
            )

            metrics = evaluate_operating_points(
                scores,
                thresholds,
                missing_threshold_policy=(context.missing_threshold_policy),
            ).with_columns(
                pl.lit(context.threshold_policy_id.value).alias(EvaluationColumn.POLICY_ID),
                pl.lit(context.seed, dtype=pl.Int64).alias(EvaluationColumn.SEED),
            )

            validate_client_metric_frame(metrics)

            self._store.write_parquet_atomic(
                job.output_path(EvaluationArtifactKey.CLIENT_METRICS),
                metrics,
            )

        except (
            OSError,
            ValueError,
            pandera_errors.SchemaError,
        ) as exc:
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
