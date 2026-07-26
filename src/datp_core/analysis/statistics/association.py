"""Pure association primitives: rank correlation and simple linear regression, with leave-one-out
leverage diagnostics."""

from __future__ import annotations

import math
from typing import cast

import numpy as np
from scipy import stats

from datp_core.analysis.statistics.models import HypothesisTestResult, LinearRegressionResult, StatisticalProcedureError


def spearman_correlation(predictor: np.ndarray, outcome: np.ndarray) -> HypothesisTestResult:
    statistic, p_value = cast("tuple[float, float]", stats.spearmanr(predictor, outcome))
    if not np.isfinite((statistic, p_value)).all():
        raise StatisticalProcedureError("Spearman correlation is undefined for the supplied observations")
    return HypothesisTestResult(test_name="spearman_correlation", statistic=float(statistic), p_value=float(p_value))


def simple_linear_regression(predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
    slope, intercept, r_value, _, standard_error = cast(
        "tuple[float, float, float, float, float]", stats.linregress(predictor, outcome)
    )
    if not np.isfinite((slope, intercept, standard_error, r_value)).all():
        raise StatisticalProcedureError("Linear regression is undefined for the supplied observations")
    centered = predictor - np.mean(predictor)
    denominator = float(np.sum(centered**2))
    if math.isclose(denominator, 0.0, abs_tol=0.0):
        raise StatisticalProcedureError("Linear regression requires non-constant predictor observations")
    leverage = tuple(float((1.0 / len(predictor)) + (value**2 / denominator)) for value in centered)
    leave_one_out_slopes = tuple(
        cast(
            "tuple[float, float, float, float, float]",
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


__all__ = ["simple_linear_regression", "spearman_correlation"]
