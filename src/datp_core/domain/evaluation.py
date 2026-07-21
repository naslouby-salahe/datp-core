"""Domain models for operating point evaluation, confusion matrices, and metrics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from math import sqrt
from statistics import mean

from .identifiers import ClientId, MetricId, ThresholdPolicyId


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
        assert fpr.value is not None and tpr.value is not None
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


def calculate_fpr_dispersion(
    values: Iterable[float], *, cv_instability_threshold: float, quantile_method: str
) -> FprDispersion:
    """Calculate unweighted cross-client FPR dispersion with explicit undefined states."""
    fprs = tuple(values)
    if not fprs:
        unavailable = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
        return FprDispersion(
            mean_fpr=unavailable,
            standard_deviation=unavailable,
            coefficient_of_variation=unavailable,
            iqr=unavailable,
            value_range=unavailable,
            worst_fpr=unavailable,
        )
    if cv_instability_threshold <= 0.0:
        raise ValueError("cv_instability_threshold must be positive")
    if quantile_method != "linear":
        raise ValueError("Only the configured linear anchor quantile interpolation is supported")
    if any(value < 0.0 or value > 1.0 for value in fprs):
        raise ValueError("FPR values must be in [0, 1]")
    average = mean(fprs)
    standard_deviation = sqrt(sum((value - average) ** 2 for value in fprs) / len(fprs))
    q25 = _linear_quantile(fprs, 0.25)
    q75 = _linear_quantile(fprs, 0.75)
    if average == 0.0:
        cv = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
    elif average < cv_instability_threshold:
        cv = MetricValue(value=standard_deviation / average, status=MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR)
    else:
        cv = MetricValue.available(standard_deviation / average)
    stable = MetricValue.available
    return FprDispersion(
        mean_fpr=stable(average),
        standard_deviation=stable(standard_deviation),
        coefficient_of_variation=cv,
        iqr=stable(q75 - q25),
        value_range=stable(max(fprs) - min(fprs)),
        worst_fpr=stable(max(fprs)),
    )


def assert_auroc_invariant(values: Iterable[float], *, tolerance: float) -> None:
    scores = tuple(values)
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    if scores and max(scores) - min(scores) > tolerance:
        raise ValueError("AUROC must be invariant across fixed-score threshold policies")


def _linear_quantile(values: tuple[float, ...], probability: float) -> float:
    ordered = tuple(sorted(values))
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + ((ordered[upper] - ordered[lower]) * fraction)


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricResultRecord:
    metric_id: MetricId
    policy_id: ThresholdPolicyId
    client_id: ClientId | None
    value: float | None
    status: MetricStatus

    def __post_init__(self) -> None:
        MetricValue(value=self.value, status=self.status)
