"""Evaluation enumerations: metric status, behavioral vocabularies, and identifiers."""

from __future__ import annotations

from enum import StrEnum


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    UNDEFINED_ZERO_DENOMINATOR = "undefined_zero_denominator"
    UNDEFINED_NEAR_ZERO_DENOMINATOR = "undefined_near_zero_denominator"
    UNAVAILABLE_MISSING_BENIGN_CLASS = "unavailable_missing_benign_class"
    UNAVAILABLE_MISSING_ATTACK_CLASS = "unavailable_missing_attack_class"
    UNAVAILABLE_INELIGIBLE_CLIENT = "unavailable_ineligible_client"
    FAILED_INVALID_ARTIFACT = "failed_invalid_artifact"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"


class MetricDirection(StrEnum):
    LOWER_IS_BETTER = "lower_is_better"
    HIGHER_IS_BETTER = "higher_is_better"
    NONE = "none"


class MetricUnit(StrEnum):
    RATIO = "ratio"
    SCORE = "score"
    SCORE_SQUARED = "score_squared"
    NONE = "none"
    COUNT = "count"
    BYTES = "bytes"


class MetricRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MODEL_QUALITY_CONTROL = "model_quality_control"
    AUXILIARY = "auxiliary"


class ZeroDenominatorPolicy(StrEnum):
    UNDEFINED_ZERO_DENOMINATOR = "undefined_zero_denominator"
    UNDEFINED_NEAR_ZERO_DENOMINATOR = "undefined_near_zero_denominator"
    RETAIN_WITH_WARNING = "retain_numerical_value_with_undefined_near_zero_denominator_warning_status"
    FORBIDDEN = "forbidden"


class MissingClassPolicy(StrEnum):
    UNAVAILABLE_MISSING_BENIGN_CLASS = "unavailable_missing_benign_class"
    UNAVAILABLE_MISSING_ATTACK_CLASS = "unavailable_missing_attack_class"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"


class QuantileEstimator(StrEnum):
    LINEAR_INTERPOLATED = "linear_interpolated_order_statistic"


class WeightingMode(StrEnum):
    NONE = "none"
    BY_COUNT = "by_count"


class MissingThresholdPolicy(StrEnum):
    FAIL = "fail"
    MARK_INELIGIBLE = "mark_ineligible"
