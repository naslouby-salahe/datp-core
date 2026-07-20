"""SciPy statistical adapters providing BCa bootstrap CI and Wilcoxon tests."""

from __future__ import annotations

import numpy as np
from scipy import stats

from datp_core.domain.statistics import ConfidenceInterval, HypothesisTestResult
from datp_core.domain.values import Probability


def compute_wilcoxon_signed_rank(x: np.ndarray, y: np.ndarray) -> HypothesisTestResult:
    """Wilcoxon signed-rank test for paired seed differences."""
    res = stats.wilcoxon(x, y, zero_method="wilcox", correction=True)
    stat_val = float(getattr(res, "statistic", 0.0))
    p_val = float(getattr(res, "pvalue", 1.0))
    return HypothesisTestResult(
        test_name="wilcoxon_signed_rank",
        statistic=stat_val,
        p_value=p_val,
    )


def compute_bca_bootstrap_ci(
    data: np.ndarray,
    resample_count: int = 1000,
    confidence_level: float = 0.95,
) -> ConfidenceInterval:
    """BCa bootstrap confidence interval estimation."""
    if len(data) < 2:
        val = float(data[0]) if len(data) == 1 else 0.0
        return ConfidenceInterval(
            lower_bound=val,
            upper_bound=val,
            confidence_level=Probability(confidence_level),
            method="single_sample",
        )

    res = stats.bootstrap((data,), np.mean, n_resamples=resample_count, confidence_level=confidence_level, method="BCa")
    return ConfidenceInterval(
        lower_bound=float(res.confidence_interval.low),
        upper_bound=float(res.confidence_interval.high),
        confidence_level=Probability(confidence_level),
        method="bca_bootstrap",
    )
