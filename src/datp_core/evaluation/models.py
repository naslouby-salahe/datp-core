"""Immutable runtime values for evaluation results and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite

from datp_core.core.identifiers import ClientId
from datp_core.evaluation.enums import MetricStatus

_VALUE_RETAINING_STATUSES = (
    MetricStatus.AVAILABLE,
    MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR,
)


def _require_finite(value: float, field_name: str) -> None:
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite, got {value}")


def _require_probability(value: float | None, field_name: str) -> None:
    if value is None:
        return

    _require_finite(value, field_name)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be in [0, 1], got {value}")


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricValue:
    value: float | None
    status: MetricStatus

    def __post_init__(self) -> None:
        retains_value = self.status in _VALUE_RETAINING_STATUSES

        if retains_value and self.value is None:
            raise ValueError(f"Metric status {self.status.value} requires a value")

        if not retains_value and self.value is not None:
            raise ValueError(f"Metric status {self.status.value} forbids a value")

        if self.value is not None:
            _require_finite(self.value, "metric value")

    @classmethod
    def available(cls, value: float) -> MetricValue:
        return cls(value=value, status=MetricStatus.AVAILABLE)

    @classmethod
    def warning(
        cls,
        value: float,
        status: MetricStatus,
    ) -> MetricValue:
        if status is not MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR:
            raise ValueError(f"{status.value} is not a value-retaining warning status")

        return cls(value=value, status=status)

    @classmethod
    def unavailable(cls, status: MetricStatus) -> MetricValue:
        if status in _VALUE_RETAINING_STATUSES:
            raise ValueError(f"Use available() or warning() for {status.value}")

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
class ClientScoreSeries:
    client_id: ClientId
    scores: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.scores:
            raise ValueError("Client score series must not be empty")

        for score in self.scores:
            _require_finite(score, "client score")
            if score < 0.0:
                raise ValueError(f"Client score must be non-negative, got {score}")


@dataclass(frozen=True, slots=True, kw_only=True)
class CdfPoint:
    score: float
    cumulative_probability: float

    def __post_init__(self) -> None:
        _require_finite(self.score, "CDF score")
        _require_probability(
            self.cumulative_probability,
            "cumulative probability",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdPosition:
    threshold: float
    benign_cdf: float | None
    attack_cdf: float | None

    def __post_init__(self) -> None:
        _require_finite(self.threshold, "threshold")
        _require_probability(self.benign_cdf, "benign CDF")
        _require_probability(self.attack_cdf, "attack CDF")


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

    def __post_init__(self) -> None:
        _require_finite(self.threshold, "threshold")

        if not isclose(
            self.threshold,
            self.threshold_position.threshold,
            rel_tol=0.0,
            abs_tol=0.0,
        ):
            raise ValueError("Distribution threshold and threshold-position threshold must match")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdTradeoff:
    client_id: ClientId
    threshold_shift: float
    fpr_delta: float | None
    tpr_delta: float | None

    def __post_init__(self) -> None:
        _require_finite(self.threshold_shift, "threshold shift")

        if self.fpr_delta is not None:
            _require_finite(self.fpr_delta, "FPR delta")

        if self.tpr_delta is not None:
            _require_finite(self.tpr_delta, "TPR delta")


@dataclass(frozen=True, slots=True, kw_only=True)
class QuantileVarianceTerms:
    within_term: float
    between_term: float
    between_ratio: float | None

    def __post_init__(self) -> None:
        _require_finite(self.within_term, "within variance")
        _require_finite(self.between_term, "between variance")

        if self.within_term < 0.0 or self.between_term < 0.0:
            raise ValueError("Variance terms must be non-negative")

        total = self.within_term + self.between_term

        if total == 0.0:
            if self.between_ratio is not None:
                raise ValueError("between_ratio must be None when total variance is zero")
            return

        if self.between_ratio is None:
            raise ValueError("between_ratio is required when total variance is positive")

        _require_probability(self.between_ratio, "between ratio")

        expected = self.between_term / total
        if not isclose(
            self.between_ratio,
            expected,
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            raise ValueError("between_ratio must equal between / (within + between)")
