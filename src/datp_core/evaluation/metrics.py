"""Pure evaluation-metric formulas: confusion-derived operating-point metrics and AUROC.

Per-client AUROC uses raw scores and labels (not threshold-based decisions), so it is identical
across B1-B4 for the same seed and frozen model -- a model-quality control only, per the roadmap,
never the thresholding verdict itself. No metric formula is implemented more than once; every
consumer imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import polars as pl
from sklearn.metrics import roc_auc_score


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
    """Typed unavailable-status metric rows for clients with no constructed threshold."""
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


class AurocStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientAuroc:
    value: float | None
    status: AurocStatus

    @classmethod
    def available(cls, value: float) -> ClientAuroc:
        return cls(value=value, status=AurocStatus.AVAILABLE)

    @classmethod
    def unavailable_single_class(cls) -> ClientAuroc:
        return cls(value=None, status=AurocStatus.UNAVAILABLE_SINGLE_CLASS)


def compute_roc_auc(labels: np.ndarray, scores: np.ndarray) -> ClientAuroc:
    if len(np.unique(labels)) < 2:
        return ClientAuroc.unavailable_single_class()
    return ClientAuroc.available(float(roc_auc_score(labels, scores)))


def compute_client_auroc(df: pl.DataFrame) -> pl.DataFrame:
    """Compute per-client AUROC from continuous anomaly scores and binary test labels.

    AUROC uses raw scores and labels (not threshold-based decisions), so it is
    identical across B1-B4 for the same seed and frozen model. Single-class
    clients receive a typed unavailable status rather than a substitute value.
    """
    if df.is_empty():
        raise ValueError("Cannot compute AUROC on empty DataFrame")
    if "score" not in df.columns or "label" not in df.columns:
        raise ValueError("AUROC computation requires score and label columns")

    auroc_records: list[dict[str, object]] = []
    for (client_id,), group in df.group_by("client_id", maintain_order=True):
        labels = group["label"].to_numpy()
        scores = group["score"].to_numpy()
        result: ClientAuroc = compute_roc_auc(labels, scores)
        auroc_records.append(
            {
                "client_id": client_id,
                "auroc": result.value,
                "auroc_status": result.status.value,
            }
        )

    return pl.DataFrame(auroc_records, schema={"client_id": pl.String, "auroc": pl.Float64, "auroc_status": pl.String})
