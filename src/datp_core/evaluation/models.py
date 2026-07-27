"""Runtime value objects for evaluation results, distributions, and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from datp_core.core.identifiers import ClientId
from datp_core.evaluation.enums import MetricStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricValue:
    value: float | None
    status: MetricStatus

    def __post_init__(self) -> None:
        if self.status is MetricStatus.AVAILABLE and self.value is None:
            raise ValueError("An available metric must have a value")
        valid_value_statuses = {MetricStatus.AVAILABLE, MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR}
        if self.status not in valid_value_statuses and self.value is not None:
            raise ValueError("An unavailable metric must not have a substitute value")
        if self.value is not None and not isfinite(self.value):
            raise ValueError(f"Metric value must be finite, got {self.value}")

    @classmethod
    def available(cls, value: float) -> MetricValue:
        return cls(value=value, status=MetricStatus.AVAILABLE)

    @classmethod
    def unavailable(cls, status: MetricStatus) -> MetricValue:
        if status is MetricStatus.AVAILABLE:
            raise ValueError("Use available() for an available metric")
        return cls(value=None, status=status)


@dataclass(frozen=True, slots=True, kw_only=True)
class FprDispersion:
    mean_fpr: MetricValue
    standard_deviation: MetricValue
    coefficient_of_variation: MetricValue
    iqr: MetricValue
    value_range: MetricValue
    worst_fpr: MetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class CdfPoint:
    score: float
    cumulative_probability: float


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdPosition:
    threshold: float
    benign_cdf: float | None
    attack_cdf: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientScoreDistribution:
    client_id: ClientId
    benign_score_cdf: tuple[CdfPoint, ...]
    attack_score_cdf: tuple[CdfPoint, ...]
    threshold_position: ThresholdPosition
    threshold: float
    false_positive_rate: MetricValue
    true_positive_rate: MetricValue
    balanced_accuracy: MetricValue
    macro_f1: MetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdTradeoff:
    client_id: ClientId
    threshold_shift: float
    fpr_delta: float | None
    tpr_delta: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class QuantileVarianceTerms:
    within_term: float
    between_term: float
    between_ratio: float | None
