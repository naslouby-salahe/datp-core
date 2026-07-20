"""Polars vector/tabular operations streaming engine."""

from __future__ import annotations

import polars as pl

from datp_core.infrastructure.tables.schemas import validate_client_metric_frame


def compute_operating_point_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Compute per-client confusion counts using the configured score-threshold comparison."""
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
            true_positive_rate=pl.when(pl.col("attack_total") > 0)
            .then(pl.col("true_positives") / pl.col("attack_total"))
            .otherwise(None),
        )
        .sort("client_id")
        .collect()
    )

    return validate_client_metric_frame(aggregated)
