"""Domain models for statistical analysis, BCa confidence intervals, and hypothesis tests."""

from __future__ import annotations

from dataclasses import dataclass

from .values import Probability, Seed


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: str

    def __post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError("Lower bound cannot be greater than upper bound")

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: str = "two-sided"


@dataclass(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    metric_name: str
    policy_a: str
    policy_b: str
    mean_difference: float
    confidence_interval: ConfidenceInterval
    hypothesis_test: HypothesisTestResult | None = None
    resample_count: int = 1000
    analysis_seed: Seed = Seed(42)
