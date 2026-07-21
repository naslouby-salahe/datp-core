"""SciPy statistical adapters providing BCa bootstrap CI and Wilcoxon tests."""

from __future__ import annotations

from typing import cast

import numpy as np
from scipy import stats

from datp_core.domain.statistics import ConfidenceInterval, HypothesisTestResult, StatisticalProcedureError
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
    if len(data) < 10:
        raise StatisticalProcedureError("BCa requires at least ten valid paired seed differences")
    if not np.isfinite(data).all():
        raise StatisticalProcedureError("BCa requires finite paired seed differences")
    if np.ptp(data) == 0.0:
        raise StatisticalProcedureError("BCa is degenerate for identical paired seed differences")

    try:
        res = stats.bootstrap(
            (data,),
            np.mean,
            n_resamples=resample_count,
            confidence_level=confidence_level,
            method="BCa",
            rng=np.random.default_rng(analysis_seed),
        )
    except ValueError as exc:
        raise StatisticalProcedureError(f"BCa failed: {exc}") from exc
    if not np.isfinite((res.confidence_interval.low, res.confidence_interval.high)).all():
        raise StatisticalProcedureError("BCa produced a non-finite confidence interval")
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
