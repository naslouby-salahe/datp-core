"""Polars vector/tabular operations streaming engine."""

from __future__ import annotations

import polars as pl


def compute_operating_point_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Compute confusion matrix and operating point metrics per client in Polars."""
    return df.group_by("client_id").agg(
        tp=(pl.col("score") >= pl.col("threshold")) & (pl.col("label") == 1),
        fp=(pl.col("score") >= pl.col("threshold")) & (pl.col("label") == 0),
        tn=(pl.col("score") < pl.col("threshold")) & (pl.col("label") == 0),
        fn=(pl.col("score") < pl.col("threshold")) & (pl.col("label") == 1),
    ).select(
        pl.col("client_id"),
        pl.col("tp").sum().alias("true_positives"),
        pl.col("fp").sum().alias("false_positives"),
        pl.col("tn").sum().alias("true_negatives"),
        pl.col("fn").sum().alias("false_negatives"),
        (
            pl.col("fp").sum() / (pl.col("fp").sum() + pl.col("tn").sum())
        ).fill_nan(0.0).alias("false_positive_rate"),
        (
            pl.col("tp").sum() / (pl.col("tp").sum() + pl.col("fn").sum())
        ).fill_nan(0.0).alias("true_positive_rate"),
    )
