"""Calibration variance decomposition."""

from __future__ import annotations

import numpy as np
import polars as pl

from datp_core.evaluation.distributions.models import QuantileVarianceTerms


def calibration_variance_terms(calibration: pl.DataFrame) -> QuantileVarianceTerms:
    values = np.asarray(calibration["score"].to_list(), dtype=np.float64)
    if values.size == 0:
        raise ValueError("Quantile-estimation analysis requires calibration scores")
    pooled_variance = float(np.var(values))
    means_and_variances: list[tuple[int, float, float]] = []
    for _, group in calibration.group_by("client_id", maintain_order=True):
        group_values = np.asarray(group["score"].to_list(), dtype=np.float64)
        means_and_variances.append((group_values.size, float(group_values.mean()), float(np.var(group_values))))
    total = sum(count for count, _, _ in means_and_variances)
    pooled_mean = float(values.mean())
    within = sum(count * variance for count, _, variance in means_and_variances) / total
    between = sum(count * (mean - pooled_mean) ** 2 for count, mean, _ in means_and_variances) / total
    return QuantileVarianceTerms(
        within_term=within,
        between_term=between,
        between_ratio=between / pooled_variance if pooled_variance else None,
    )
