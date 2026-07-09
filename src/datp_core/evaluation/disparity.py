"""Per-seed FPR disparity summaries for the locked anchor endpoint."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp_core.evaluation.classification import ClientMetrics, MetricError


@dataclass(frozen=True)
class DisparityMetrics:
    cv_fpr: float
    iqr_fpr: float
    max_minus_min_fpr: float
    worst_client_fpr: float


def compute_fpr_disparity(metrics: tuple[ClientMetrics, ...]) -> DisparityMetrics:
    fpr = np.asarray([metric.fpr for metric in metrics], dtype=float)
    if len(fpr) < 2:
        raise MetricError("CV(FPR) requires at least two eligible clients")
    if np.isclose(float(fpr.mean()), 0.0):
        raise MetricError("CV(FPR) is undefined when mean FPR is zero")
    return DisparityMetrics(
        cv_fpr=float(fpr.std(ddof=1) / fpr.mean()),
        iqr_fpr=float(np.quantile(fpr, 0.75) - np.quantile(fpr, 0.25)),
        max_minus_min_fpr=float(fpr.max() - fpr.min()),
        worst_client_fpr=float(fpr.max()),
    )
