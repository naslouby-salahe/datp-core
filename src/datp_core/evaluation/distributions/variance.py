"""Calibration variance decomposition."""

from __future__ import annotations

import polars as pl

from datp_core.evaluation.distributions.models import QuantileVarianceTerms


def calibration_variance_terms(calibration: pl.DataFrame) -> QuantileVarianceTerms:
    if calibration.height == 0:
        raise ValueError("Quantile-estimation analysis requires calibration scores")
    # Polars-native aggregation eliminates Python group iteration and numpy bridge
    scores = calibration["score"]
    pooled_mean = scores.mean()
    pooled_variance = scores.var(ddof=0)
    group_stats = calibration.group_by("client_id").agg(
        pl.len().alias("count"),
        pl.col("score").mean().alias("mean"),
        pl.col("score").var(ddof=0).alias("variance"),
    )
    total = group_stats["count"].sum()
    within = float((group_stats["count"] * group_stats["variance"]).sum() / total)
    between = float((group_stats["count"] * (group_stats["mean"] - pooled_mean) ** 2).sum() / total)
    return QuantileVarianceTerms(
        within_term=within,
        between_term=between,
        between_ratio=between / pooled_variance if pooled_variance else None,
    )
