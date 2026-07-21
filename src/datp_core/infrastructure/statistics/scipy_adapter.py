"""SciPy statistical adapters providing BCa bootstrap CI and Wilcoxon tests."""

from __future__ import annotations

from typing import cast

import numpy as np
from scipy import stats

from datp_core.domain.statistics import ConfidenceInterval, HypothesisTestResult
from datp_core.domain.values import Probability


def _compute_wilcoxon_signed_rank(x: np.ndarray, y: np.ndarray) -> HypothesisTestResult:
    """Wilcoxon signed-rank test for paired seed differences."""
    res = stats.wilcoxon(x, y, zero_method="wilcox", correction=True)
    statistic, p_value = cast(tuple[float, float], res)
    stat_val = float(statistic)
    p_val = float(p_value)
    return HypothesisTestResult(
        test_name="wilcoxon_signed_rank",
        statistic=stat_val,
        p_value=p_val,
    )


def _compute_bca_bootstrap_ci(
    data: np.ndarray,
    resample_count: int,
    confidence_level: float,
    analysis_seed: int,
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

    res = stats.bootstrap(
        (data,),
        np.mean,
        n_resamples=resample_count,
        confidence_level=confidence_level,
        method="BCa",
        rng=np.random.default_rng(analysis_seed),
    )
    return ConfidenceInterval(
        lower_bound=float(res.confidence_interval.low),
        upper_bound=float(res.confidence_interval.high),
        confidence_level=Probability(confidence_level),
        method="bca_bootstrap",
    )


class ScipyStatisticalAnalysisAdapter:
    """SciPy implementation of the application statistical-analysis port."""

    def bootstrap_ci(
        self,
        data: np.ndarray,
        resample_count: int,
        confidence_level: float,
        analysis_seed: int,
    ) -> ConfidenceInterval:
        return _compute_bca_bootstrap_ci(
            data,
            resample_count=resample_count,
            confidence_level=confidence_level,
            analysis_seed=analysis_seed,
        )

    def wilcoxon(self, left: np.ndarray, right: np.ndarray) -> HypothesisTestResult:
        return _compute_wilcoxon_signed_rank(left, right)
