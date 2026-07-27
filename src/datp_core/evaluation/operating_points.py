"""Operating-point evaluation: confusion counts, per-client metrics, AUROC."""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.metrics import roc_auc_score

from datp_core.evaluation.enums import MetricStatus, MissingThresholdPolicy

_OPERATING_POINT_RESULT_SCHEMA: dict[str, type] = {
    "client_id": pl.String,
    "true_positives": pl.Int64,
    "false_positives": pl.Int64,
    "true_negatives": pl.Int64,
    "false_negatives": pl.Int64,
    "false_positive_rate": pl.Float64,
    "false_positive_rate_status": pl.String,
    "true_positive_rate": pl.Float64,
    "true_positive_rate_status": pl.String,
    "balanced_accuracy": pl.Float64,
    "balanced_accuracy_status": pl.String,
    "macro_f1": pl.Float64,
    "macro_f1_status": pl.String,
    "auroc": pl.Float64,
    "auroc_status": pl.String,
}
_OPERATING_POINT_RESULT_COLUMNS: tuple[str, ...] = tuple(_OPERATING_POINT_RESULT_SCHEMA)


def _validate_input_columns(df: pl.DataFrame, required: tuple[str, ...], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def evaluate_operating_points(
    scores: pl.DataFrame,
    thresholds: pl.DataFrame,
    *,
    missing_threshold_policy: MissingThresholdPolicy,
) -> pl.DataFrame:
    """Compute per-client operating-point metrics and AUROC.

    Produces one canonical output schema for all scored clients.
    Eligible and ineligible rows share identical columns and dtypes.
    AUROC is computed for every scored client independently of threshold eligibility.
    """
    _validate_input_columns(scores, ("client_id", "score", "label"), "Scores")
    _validate_input_columns(thresholds, ("client_id", "threshold"), "Thresholds")
    if scores.is_empty():
        raise ValueError("Cannot evaluate operating points on empty scores DataFrame")

    _validate_finite_scores(scores)
    _validate_finite_thresholds(thresholds)

    score_client_ids = scores["client_id"]
    if score_client_ids.is_null().any():
        raise ValueError("Scores contain null client_id values")
    threshold_client_ids = thresholds["client_id"]
    if threshold_client_ids.is_null().any():
        raise ValueError("Thresholds contain null client_id values")
    if threshold_client_ids.is_duplicated().any():
        raise ValueError("Thresholds contain duplicate client_id values")

    joined = scores.join(
        thresholds.select("client_id", "threshold"),
        on="client_id",
        how="left",
        validate="m:1",
    )

    eligible = joined.filter(pl.col("threshold").is_not_null())

    if joined["threshold"].null_count() > 0:
        if missing_threshold_policy is MissingThresholdPolicy.FAIL:
            missing_clients = joined.filter(pl.col("threshold").is_null()).select("client_id").unique()
            raise ValueError(
                f"Threshold artifact does not cover every scored client: {missing_clients['client_id'].to_list()}"
            )
        ineligible = _build_ineligible_rows(joined)
        if eligible.is_empty():
            metrics = ineligible
        else:
            eligible_metrics = _compute_eligible_metrics(eligible)
            metrics = pl.concat((eligible_metrics, ineligible), how="vertical")
    else:
        metrics = _compute_eligible_metrics(eligible)

    auroc = _compute_auroc_all_clients(scores)
    metrics = metrics.join(auroc, on="client_id", how="left", validate="m:1")

    metrics = metrics.select(_OPERATING_POINT_RESULT_COLUMNS).sort("client_id")

    if metrics.is_duplicated().any():
        raise ValueError("Result contains duplicate rows")
    if metrics["client_id"].n_unique() != metrics.height:
        raise ValueError("Result has duplicate client_id values")
    if metrics["auroc"].is_null().any() and metrics["auroc_status"].is_null().any():
        raise ValueError("Result is missing AUROC rows")

    return metrics


def _validate_finite_scores(df: pl.DataFrame) -> None:
    score_col = df["score"]
    if score_col.is_null().any():
        raise ValueError("Scores contain null values")
    if score_col.is_nan().any():
        raise ValueError("Scores contain NaN values")
    if score_col.is_infinite().any():
        raise ValueError("Scores contain infinite values")
    if "label" in df.columns:
        label_col = df["label"]
        unique_labels = label_col.unique().to_list()
        if any(label not in (0, 1) for label in unique_labels):
            raise ValueError(f"Labels must be binary (0 or 1), found: {unique_labels}")


def _validate_finite_thresholds(df: pl.DataFrame) -> None:
    if "threshold" not in df.columns:
        return
    threshold_col = df["threshold"]
    non_null = threshold_col.drop_nulls()
    if non_null.is_nan().any():
        raise ValueError("Thresholds contain NaN values")
    if non_null.is_infinite().any():
        raise ValueError("Thresholds contain infinite values")


def _compute_eligible_metrics(df: pl.DataFrame) -> pl.DataFrame:
    return (
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
            .then(pl.lit(MetricStatus.AVAILABLE.value))
            .otherwise(pl.lit(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value)),
            true_positive_rate=pl.when(pl.col("attack_total") > 0)
            .then(pl.col("true_positives") / pl.col("attack_total"))
            .otherwise(None),
            true_positive_rate_status=pl.when(pl.col("attack_total") > 0)
            .then(pl.lit(MetricStatus.AVAILABLE.value))
            .otherwise(pl.lit(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value)),
        )
        .with_columns(
            balanced_accuracy=pl.when((pl.col("benign_total") > 0) & (pl.col("attack_total") > 0))
            .then((pl.col("true_positive_rate") + (1.0 - pl.col("false_positive_rate"))) / 2.0)
            .otherwise(None),
            balanced_accuracy_status=pl.when(pl.col("benign_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value))
            .when(pl.col("attack_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value))
            .otherwise(pl.lit(MetricStatus.AVAILABLE.value)),
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
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value))
            .when(pl.col("attack_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value))
            .otherwise(pl.lit(MetricStatus.AVAILABLE.value)),
        )
        .drop("benign_total", "attack_total")
        .sort("client_id")
        .collect()
    )


def _build_ineligible_rows(joined: pl.DataFrame) -> pl.DataFrame:
    ineligible_status = MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value
    return (
        joined.filter(pl.col("threshold").is_null())
        .select("client_id")
        .unique(maintain_order=True)
        .with_columns(
            pl.lit(None, dtype=pl.Int64).alias("true_positives"),
            pl.lit(None, dtype=pl.Int64).alias("false_positives"),
            pl.lit(None, dtype=pl.Int64).alias("true_negatives"),
            pl.lit(None, dtype=pl.Int64).alias("false_negatives"),
            pl.lit(None, dtype=pl.Float64).alias("false_positive_rate"),
            pl.lit(ineligible_status).alias("false_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("true_positive_rate"),
            pl.lit(ineligible_status).alias("true_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("balanced_accuracy"),
            pl.lit(ineligible_status).alias("balanced_accuracy_status"),
            pl.lit(None, dtype=pl.Float64).alias("macro_f1"),
            pl.lit(ineligible_status).alias("macro_f1_status"),
        )
    )


def _compute_auroc_all_clients(scores: pl.DataFrame) -> pl.DataFrame:
    if "score" not in scores.columns or "label" not in scores.columns:
        raise ValueError("AUROC computation requires score and label columns")

    grouped = scores.group_by("client_id", maintain_order=True).agg(
        pl.col("label").alias("_labels"),
        pl.col("score").alias("_scores"),
    )

    result_client_ids: list[str] = []
    result_aurocs: list[float | None] = []
    result_statuses: list[str] = []
    for row in grouped.iter_rows(named=True):
        labels_array = np.asarray(row["_labels"], dtype=np.int64)
        scores_array = np.asarray(row["_scores"], dtype=np.float64)
        result_client_ids.append(str(row["client_id"]))
        if len(np.unique(labels_array)) < 2:
            result_aurocs.append(None)
            result_statuses.append(MetricStatus.UNAVAILABLE_SINGLE_CLASS.value)
        else:
            result_aurocs.append(float(roc_auc_score(labels_array, scores_array)))
            result_statuses.append(MetricStatus.AVAILABLE.value)

    return pl.DataFrame(
        {
            "client_id": result_client_ids,
            "auroc": result_aurocs,
            "auroc_status": result_statuses,
        },
        schema={"client_id": pl.String, "auroc": pl.Float64, "auroc_status": pl.String},
    )
