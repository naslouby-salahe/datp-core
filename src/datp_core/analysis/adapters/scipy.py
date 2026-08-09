"""Typed extraction boundaries for SciPy result objects."""

from math import isfinite
from typing import Protocol, SupportsFloat


class StatisticPValueResult(Protocol):
    statistic: SupportsFloat
    pvalue: SupportsFloat


class LinearRegressionResult(Protocol):
    intercept: SupportsFloat
    slope: SupportsFloat
    stderr: SupportsFloat
    rvalue: SupportsFloat


def statistic_p_value(result: StatisticPValueResult) -> tuple[float, float] | None:
    statistic, pvalue = float(result.statistic), float(result.pvalue)
    if not all(isfinite(value) for value in (statistic, pvalue)):
        return None
    return statistic, pvalue


def linear_regression_values(
    result: LinearRegressionResult,
) -> tuple[float, float, float, float] | None: #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    intercept, slope, stderr, rvalue = (
        float(result.intercept),
        float(result.slope),
        float(result.stderr),
        float(result.rvalue),
    )
    if not all(isfinite(value) for value in (intercept, slope, stderr, rvalue)):
        return None
    return intercept, slope, stderr, rvalue
