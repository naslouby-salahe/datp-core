"""Operating-point evaluation from planner-supplied threshold and test-score files."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_test_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.evaluation.metrics.auroc import compute_client_auroc
from datp_core.evaluation.metrics.operating_point import compute_operating_point_metrics, ineligible_client_metrics
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class OperatingPointEvaluationStageHandler:
    stage = StageKind.OPERATING_POINT_EVALUATION

    def __init__(self, config: ResolvedProjectConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        try:
            thresholds = validate_threshold_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("thresholds"))))
            )
            scores = validate_test_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("test_scores"))))
            )
            joined = scores.join(thresholds.select("client_id", "threshold"),
                                 on="client_id", how="left")
            if joined["threshold"].null_count() > 0 and job.context.calibration_sample_count is None:
                raise ValueError("Threshold artifact does not cover every scored client")
            eligible = joined.filter(pl.col("threshold").is_not_null())
            if eligible.is_empty():
                metrics = ineligible_client_metrics(joined)
            elif joined["threshold"].null_count() > 0:
                metrics = pl.concat((compute_operating_point_metrics(
                    eligible), ineligible_client_metrics(joined)))
            else:
                metrics = compute_operating_point_metrics(eligible)
            metrics = metrics.join(compute_client_auroc(scores), on="client_id", how="left")
            metrics = metrics.with_columns(
                pl.lit(job.context.threshold_policy_id.value if job.context.threshold_policy_id else None).alias(
                    "policy_id"
                ),
                pl.lit(job.context.seed).alias("seed"),
            )
            validate_client_metric_frame(metrics)
            payload = BytesIO()
            metrics.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("client_metrics"), payload.getvalue())
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
