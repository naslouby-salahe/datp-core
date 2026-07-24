"""Shared statistical value types used across every analysis capability."""

from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import MetricId, ThresholdPolicyId
from datp_core.core.values import Probability, Seed


class StatisticalProcedureError(ValueError):
    """A locked statistical procedure cannot produce a scientifically valid result."""


@define(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: str

    def __attrs_post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError("Lower bound cannot be greater than upper bound")

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@define(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: str = "two-sided"


@define(frozen=True, slots=True, kw_only=True)
class LinearRegressionResult:
    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


__all__ = [
    "ConfidenceInterval",
    "HypothesisTestResult",
    "LinearRegressionResult",
    "PairedSeedDifferenceRecord",
    "StatisticalProcedureError",
]
