"""Metric status, value, confusion matrix, and dispersion models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from datp_core.core.identifiers import ClientId


class MetricStatus(Enum):
    AVAILABLE = "available"
    UNDEFINED_ZERO_DENOMINATOR = "undefined_zero_denominator"
    UNDEFINED_NEAR_ZERO_DENOMINATOR = "undefined_near_zero_denominator"
    UNAVAILABLE_MISSING_BENIGN_CLASS = "unavailable_missing_benign_class"
    UNAVAILABLE_MISSING_ATTACK_CLASS = "unavailable_missing_attack_class"
    UNAVAILABLE_INVALID_ATTACK_ASSIGNMENT = "unavailable_invalid_attack_assignment"
    UNAVAILABLE_INELIGIBLE_CLIENT = "unavailable_ineligible_client"
    UNAVAILABLE_UNSUPPORTED_REGIME = "unavailable_unsupported_regime"
    FAILED_INVALID_ARTIFACT = "failed_invalid_artifact"
    FAILED_STATISTICAL_PROCEDURE = "failed_statistical_procedure"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"


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

    @classmethod
    def available(cls, value: float) -> MetricValue:
        return cls(value=value, status=MetricStatus.AVAILABLE)

    @classmethod
    def unavailable(cls, status: MetricStatus) -> MetricValue:
        if status is MetricStatus.AVAILABLE:
            raise ValueError("Use available() for an available metric")
        return cls(value=None, status=status)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientConfusionMatrix:
    client_id: ClientId
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    def __post_init__(self) -> None:
        if any(v < 0 for v in (self.true_positives, self.false_positives, self.true_negatives, self.false_negatives)):
            raise ValueError("Confusion matrix counts must be non-negative")

    @property
    def false_positive_rate(self) -> MetricValue:
        total_negatives = self.false_positives + self.true_negatives
        if total_negatives == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS)
        return MetricValue.available(self.false_positives / total_negatives)

    @property
    def true_positive_rate(self) -> MetricValue:
        total_positives = self.true_positives + self.false_negatives
        if total_positives == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS)
        return MetricValue.available(self.true_positives / total_positives)

    @property
    def balanced_accuracy(self) -> MetricValue:
        fpr = self.false_positive_rate
        tpr = self.true_positive_rate
        if fpr.status is not MetricStatus.AVAILABLE:
            return MetricValue.unavailable(fpr.status)
        if tpr.status is not MetricStatus.AVAILABLE:
            return MetricValue.unavailable(tpr.status)
        if fpr.value is None or tpr.value is None:
            raise ValueError("Available metric must have a value")
        return MetricValue.available((tpr.value + (1.0 - fpr.value)) / 2.0)

    @property
    def macro_f1(self) -> MetricValue:
        benign_support = self.true_negatives + self.false_positives
        attack_support = self.true_positives + self.false_negatives
        benign_denominator = (2 * self.true_negatives) + self.false_positives + self.false_negatives
        attack_denominator = (2 * self.true_positives) + self.false_positives + self.false_negatives
        if benign_support == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS)
        if attack_support == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS)
        if benign_denominator == 0 or attack_denominator == 0:
            return MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
        benign_f1 = (2 * self.true_negatives) / benign_denominator
        attack_f1 = (2 * self.true_positives) / attack_denominator
        return MetricValue.available((benign_f1 + attack_f1) / 2.0)


@dataclass(frozen=True, slots=True, kw_only=True)
class FprDispersion:
    mean_fpr: MetricValue
    standard_deviation: MetricValue
    coefficient_of_variation: MetricValue
    iqr: MetricValue
    value_range: MetricValue
    worst_fpr: MetricValue
