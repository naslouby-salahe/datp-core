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
    return _finite_values(result.statistic, result.pvalue)


def linear_regression_values(
    result: LinearRegressionResult,
) -> tuple[float, float, float, float] | None:
    return _finite_values(
        result.intercept,
        result.slope,
        result.stderr,
        result.rvalue,
    )


def _finite_values(*values: SupportsFloat) -> tuple[float, ...] | None:
    converted = tuple(float(value) for value in values)
    return converted if all(isfinite(value) for value in converted) else None
