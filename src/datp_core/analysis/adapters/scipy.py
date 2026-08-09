"""Typed extraction boundaries for SciPy result objects."""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol, SupportsFloat

from datp_core.core.numeric import MetricValue


class StatisticPValueResult(Protocol):
    statistic: SupportsFloat
    pvalue: SupportsFloat


class LinearRegressionResult(Protocol):
    intercept: SupportsFloat
    slope: SupportsFloat
    stderr: SupportsFloat
    rvalue: SupportsFloat


@dataclass(frozen=True, slots=True)
class StatisticPValueValues:
    statistic: MetricValue
    p_value: MetricValue


@dataclass(frozen=True, slots=True)
class LinearRegressionValues:
    intercept: MetricValue
    slope: MetricValue
    stderr: MetricValue
    rvalue: MetricValue


def statistic_p_value(result: StatisticPValueResult) -> StatisticPValueValues | None:
    statistic, pvalue = float(result.statistic), float(result.pvalue)
    if not all(isfinite(value) for value in (statistic, pvalue)):
        return None
    return StatisticPValueValues(statistic=MetricValue(statistic), p_value=MetricValue(pvalue))


def linear_regression_values(result: LinearRegressionResult) -> LinearRegressionValues | None:
    intercept, slope, stderr, rvalue = (
        float(result.intercept),
        float(result.slope),
        float(result.stderr),
        float(result.rvalue),
    )
    if not all(isfinite(value) for value in (intercept, slope, stderr, rvalue)):
        return None
    return LinearRegressionValues(
        intercept=MetricValue(intercept),
        slope=MetricValue(slope),
        stderr=MetricValue(stderr),
        rvalue=MetricValue(rvalue),
    )
