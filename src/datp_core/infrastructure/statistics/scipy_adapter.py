"""SciPy statistical adapters providing BCa bootstrap CI and Wilcoxon tests."""

from __future__ import annotations

from typing import cast

import numpy as np
from scipy import stats

from datp_core.domain.statistics import (
    ConfidenceInterval,
    HypothesisTestResult,
    LinearRegressionResult,
    StatisticalProcedureError,
)
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
    method: str,
) -> ConfidenceInterval:
    """BCa bootstrap confidence interval estimation."""
    if method == "bca_bootstrap" and len(data) < 10:
        raise StatisticalProcedureError("BCa requires at least ten valid paired seed differences")
    if method == "percentile_bootstrap" and len(data) < 2:
        raise StatisticalProcedureError("Percentile bootstrap requires at least two valid paired seed differences")
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
            method="BCa" if method == "bca_bootstrap" else "percentile",
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
        method=method,
    )


def _compute_spearman(predictor: np.ndarray, outcome: np.ndarray) -> HypothesisTestResult:
    statistic, p_value = cast(tuple[float, float], stats.spearmanr(predictor, outcome))
    if not np.isfinite((statistic, p_value)).all():
        raise StatisticalProcedureError("Spearman correlation is undefined for the supplied observations")
    return HypothesisTestResult(test_name="spearman_correlation", statistic=float(statistic), p_value=float(p_value))


def _compute_linear_regression(predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
    slope, intercept, r_value, _, standard_error = cast(
        tuple[float, float, float, float, float], stats.linregress(predictor, outcome)
    )
    if not np.isfinite((slope, intercept, standard_error, r_value)).all():
        raise StatisticalProcedureError("Linear regression is undefined for the supplied observations")
    centered = predictor - np.mean(predictor)
    denominator = float(np.sum(centered**2))
    if denominator == 0.0:
        raise StatisticalProcedureError("Linear regression requires non-constant predictor observations")
    leverage = tuple(float((1.0 / len(predictor)) + (value**2 / denominator)) for value in centered)
    leave_one_out_slopes = tuple(
        cast(
            tuple[float, float, float, float, float],
            stats.linregress(np.delete(predictor, index), np.delete(outcome, index)),
        )[0]
        for index in range(len(predictor))
    )
    return LinearRegressionResult(
        slope=float(slope),
        intercept=float(intercept),
        standard_error=float(standard_error),
        r_squared=float(r_value**2),
        leverage=leverage,
        leave_one_out_slopes=leave_one_out_slopes,
    )


class ScipyStatisticalAnalysisAdapter:
    """SciPy implementation of the application statistical-analysis port."""

    def bootstrap_ci(
        self,
        data: np.ndarray,
        resample_count: int,
        confidence_level: float,
        analysis_seed: int,
        method: str,
    ) -> ConfidenceInterval:
        return _compute_bca_bootstrap_ci(
            data,
            resample_count=resample_count,
            confidence_level=confidence_level,
            analysis_seed=analysis_seed,
            method=method,
        )

    def wilcoxon(self, left: np.ndarray, right: np.ndarray) -> HypothesisTestResult:
        return _compute_wilcoxon_signed_rank(left, right)

    def spearman(self, predictor: np.ndarray, outcome: np.ndarray) -> HypothesisTestResult:
        return _compute_spearman(predictor, outcome)

    def linear_regression(self, predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
        return _compute_linear_regression(predictor, outcome)
