"""Per-client confusion-count/operating-point metrics, and the operating-point evaluation stage.

`ineligible_client_metrics` is the single canonical home for a helper that was previously
byte-for-byte duplicated in `application/learning_stages.py` and `application/threshold_stages.py`
(confirmed in CURRENT_ARCHITECTURE.md) -- both now import it from here instead.
"""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.models import ArtifactFormat, ArtifactRepository, BytesPayload
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.evaluation.predictive_metrics import compute_client_auroc
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.sweeps import score_context
from datp_core.pipeline.frames import validate_client_metric_frame, validate_test_score_frame, validate_threshold_frame
from datp_core.pipeline.identifiers import RunId
from datp_core.pipeline.models import StageJob, StageJobOutcome, StageKind
from datp_core.pipeline.stages import artifact_parents, commit_artifact


def compute_operating_point_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Compute per-client confusion counts using the configured score-threshold comparison.

    Returns a DataFrame with all confusion-count and derived-metric columns EXCEPT
    AUROC, which is computed separately via ``compute_client_auroc`` and joined
    by the caller before final schema validation.
    """
    if df.is_empty():
        raise ValueError("Cannot compute operating point metrics on empty DataFrame")

    # Verify score non-finiteness
    if df["score"].is_nan().any() or df["score"].is_null().any():
        raise ValueError("Non-finite or null scores found in evaluation frame")

    # Anomaly prediction rule: score > threshold (strict inequality)
    aggregated = (
        df.lazy()
        .with_columns(
            is_pred_attack=(pl.col("score") > pl.col("threshold")).cast(pl.Int64),
            is_benign=(pl.col("label") == 0).cast(pl.Int64),
            is_attack=(pl.col("label") == 1).cast(pl.Int64),
        )
        .with_columns(
            tp=pl.col("is_pred_attack") * pl.col("is_attack"),
            fp=pl.col("is_pred_attack") * pl.col("is_benign"),
            tn=(1 - pl.col("is_pred_attack")) * pl.col("is_benign"),
            fn=(1 - pl.col("is_pred_attack")) * pl.col("is_attack"),
        )
        .group_by("client_id")
        .agg(
            true_positives=pl.col("tp").sum(),
            false_positives=pl.col("fp").sum(),
            true_negatives=pl.col("tn").sum(),
            false_negatives=pl.col("fn").sum(),
        )
        .with_columns(
            benign_total=pl.col("false_positives") + pl.col("true_negatives"),
            attack_total=pl.col("true_positives") + pl.col("false_negatives"),
        )
        .with_columns(
            false_positive_rate=pl.when(pl.col("benign_total") > 0)
            .then(pl.col("false_positives") / pl.col("benign_total"))
            .otherwise(None),
            false_positive_rate_status=pl.when(pl.col("benign_total") > 0)
            .then(pl.lit("available"))
            .otherwise(pl.lit("unavailable_missing_benign_class")),
            true_positive_rate=pl.when(pl.col("attack_total") > 0)
            .then(pl.col("true_positives") / pl.col("attack_total"))
            .otherwise(None),
            true_positive_rate_status=pl.when(pl.col("attack_total") > 0)
            .then(pl.lit("available"))
            .otherwise(pl.lit("unavailable_missing_attack_class")),
        )
        .with_columns(
            balanced_accuracy=pl.when((pl.col("benign_total") > 0) & (pl.col("attack_total") > 0))
            .then((pl.col("true_positive_rate") + (1.0 - pl.col("false_positive_rate"))) / 2.0)
            .otherwise(None),
            balanced_accuracy_status=pl.when(pl.col("benign_total") == 0)
            .then(pl.lit("unavailable_missing_benign_class"))
            .when(pl.col("attack_total") == 0)
            .then(pl.lit("unavailable_missing_attack_class"))
            .otherwise(pl.lit("available")),
            macro_f1=pl.when((pl.col("benign_total") > 0) & (pl.col("attack_total") > 0))
            .then(
                (
                    (
                        (2.0 * pl.col("true_negatives"))
                        / ((2.0 * pl.col("true_negatives")) + pl.col("false_positives") + pl.col("false_negatives"))
                    )
                    + (
                        (2.0 * pl.col("true_positives"))
                        / ((2.0 * pl.col("true_positives")) + pl.col("false_positives") + pl.col("false_negatives"))
                    )
                )
                / 2.0
            )
            .otherwise(None),
            macro_f1_status=pl.when(pl.col("benign_total") == 0)
            .then(pl.lit("unavailable_missing_benign_class"))
            .when(pl.col("attack_total") == 0)
            .then(pl.lit("unavailable_missing_attack_class"))
            .otherwise(pl.lit("available")),
        )
        .sort("client_id")
        .collect()
    )
    return aggregated


def ineligible_client_metrics(evaluation: pl.DataFrame) -> pl.DataFrame:
    """Typed unavailable-status metric rows for clients with no constructed threshold.

    The single canonical implementation of a helper previously duplicated byte-for-byte in
    `application/learning_stages.py` and `application/threshold_stages.py`.
    """
    return (
        evaluation.filter(pl.col("threshold").is_null())
        .select("client_id")
        .unique(maintain_order=True)
        .with_columns(
            pl.lit(0).alias("true_positives"),
            pl.lit(0).alias("false_positives"),
            pl.lit(0).alias("true_negatives"),
            pl.lit(0).alias("false_negatives"),
            pl.lit(None, dtype=pl.Float64).alias("false_positive_rate"),
            pl.lit("unavailable_ineligible_client").alias("false_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("true_positive_rate"),
            pl.lit("unavailable_ineligible_client").alias("true_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("balanced_accuracy"),
            pl.lit("unavailable_ineligible_client").alias("balanced_accuracy_status"),
            pl.lit(None, dtype=pl.Float64).alias("macro_f1"),
            pl.lit("unavailable_ineligible_client").alias("macro_f1_status"),
            pl.lit(None, dtype=pl.Float64).alias("auroc"),
            pl.lit("unavailable_ineligible_client").alias("auroc_status"),
        )
    )


class OperatingPointEvaluationStageHandler:
    """Evaluate configured thresholds against immutable test scores without score reuse across roles."""

    stage = StageKind.OPERATING_POINT_EVALUATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        thresholds = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(job.context).value}")
        scores = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(score_context(job.context)).value}"
        )
        if not thresholds.found or thresholds.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Threshold artifact is unavailable"
            )
        if not scores.found or scores.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Test score artifact is unavailable"
            )
        try:
            threshold_frame = validate_threshold_frame(pl.read_parquet(BytesIO(thresholds.payload_bytes)))
            score_frame = validate_test_score_frame(pl.read_parquet(BytesIO(scores.payload_bytes)))
            evaluation = score_frame.join(threshold_frame.select("client_id", "threshold"), on="client_id", how="left")
            if evaluation["threshold"].null_count() > 0 and job.context.calibration_sample_count is None:
                raise ValueError("Threshold artifact does not cover every scored client")
            eligible = evaluation.filter(pl.col("threshold").is_not_null())
            if eligible.is_empty():
                metrics = ineligible_client_metrics(evaluation)
            elif evaluation["threshold"].null_count() > 0:
                metrics = pl.concat((compute_operating_point_metrics(eligible), ineligible_client_metrics(evaluation)))
            else:
                metrics = compute_operating_point_metrics(eligible)
            auroc = compute_client_auroc(score_frame)
            metrics = metrics.join(auroc, on="client_id", how="left")
            metrics = metrics.with_columns(
                pl.lit(job.context.threshold_policy_id.value if job.context.threshold_policy_id else None).alias(
                    "policy_id"
                ),
                pl.lit(job.context.seed).alias("seed"),
            )
            validate_client_metric_frame(metrics)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        metrics.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "metric artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
