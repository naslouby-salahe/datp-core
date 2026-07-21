"""Domain models for statistical analysis, BCa confidence intervals, and hypothesis tests."""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

from attrs import define

from datp_core.domain.identifiers import MetricId, ThresholdPolicyId
from datp_core.domain.values import Probability, Seed


class StatisticalProcedureError(ValueError):
    """A locked statistical procedure cannot produce a scientifically valid result."""


def matched_pairs_rank_biserial_correlation(left: Iterable[float], right: Iterable[float]) -> float:
    """Return the signed-rank effect size for paired observations, with average tie ranks."""
    differences = tuple(float(a) - float(b) for a, b in zip(left, right, strict=True))
    if not differences or not all(isfinite(value) for value in differences):
        raise StatisticalProcedureError("Rank-biserial correlation requires finite paired observations")
    nonzero = tuple(value for value in differences if value != 0.0)
    if not nonzero:
        raise StatisticalProcedureError("Rank-biserial correlation is undefined when all paired differences are zero")
    ranks = _average_ranks(tuple(abs(value) for value in nonzero))
    positive = sum(rank for difference, rank in zip(nonzero, ranks, strict=True) if difference > 0.0)
    negative = sum(rank for difference, rank in zip(nonzero, ranks, strict=True) if difference < 0.0)
    return (positive - negative) / (positive + negative)


def holm_adjust_p_values(values: Iterable[float]) -> tuple[float, ...]:
    """Apply the Holm step-down correction and return values in the original order."""
    p_values = tuple(float(value) for value in values)
    if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in p_values):
        raise StatisticalProcedureError("Holm correction requires finite p-values in [0, 1]")
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, (index, p_value) in enumerate(ordered):
        corrected = min(1.0, (len(p_values) - rank) * p_value)
        previous = max(previous, corrected)
        adjusted[index] = previous
    return tuple(adjusted)


def _average_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    ranks = [0.0] * len(values)
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for index, _ in ordered[start:end]:
            ranks[index] = average_rank
        start = end
    return tuple(ranks)


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
