"""Typed evaluation vocabularies and identifiers."""

from __future__ import annotations

from enum import StrEnum


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    UNDEFINED_ZERO_DENOMINATOR = "undefined_zero_denominator"
    UNDEFINED_NEAR_ZERO_DENOMINATOR = "undefined_near_zero_denominator"
    UNAVAILABLE_MISSING_BENIGN_CLASS = "unavailable_missing_benign_class"
    UNAVAILABLE_MISSING_ATTACK_CLASS = "unavailable_missing_attack_class"
    UNAVAILABLE_INELIGIBLE_CLIENT = "unavailable_ineligible_client"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"
    FAILED_INVALID_ARTIFACT = "failed_invalid_artifact"


class MissingThresholdPolicy(StrEnum):
    FAIL = "fail"
    MARK_INELIGIBLE = "mark_ineligible"


class PredictionRule(StrEnum):
    SCORE_GREATER_THAN_THRESHOLD = "score > threshold"


class MetricDirection(StrEnum):
    LOWER_IS_BETTER = "lower_is_better"
    HIGHER_IS_BETTER = "higher_is_better"
    NONE = "none"


class MetricUnit(StrEnum):
    RATIO = "ratio"
    SCORE = "score"
    SCORE_SQUARED = "score_squared"
    COUNT = "count"
    BYTES = "bytes"
    NONE = "none"


class MetricRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MODEL_QUALITY_CONTROL = "model_quality_control"
    AUXILIARY = "auxiliary"


class MetricRequirement(StrEnum):
    BENIGN_CLASS = "benign_class"
    ATTACK_CLASS = "attack_class"
    BOTH_CLASSES = "both_classes"
    THRESHOLD = "threshold"
    MULTIPLE_CLIENTS = "multiple_clients"


class ZeroDenominatorPolicy(StrEnum):
    UNAVAILABLE = "unavailable"
    RETAIN_WITH_WARNING = "retain_with_warning"
    FORBIDDEN = "forbidden"


class MissingClassPolicy(StrEnum):
    REPORT_MISSING_BENIGN_CLASS = "report_missing_benign_class"
    REPORT_MISSING_ATTACK_CLASS = "report_missing_attack_class"
    REPORT_SINGLE_CLASS = "report_single_class"


class QuantileEstimator(StrEnum):
    LINEAR_INTERPOLATED_ORDER_STATISTIC = "linear_interpolated_order_statistic"


class WeightingMode(StrEnum):
    UNWEIGHTED = "unweighted"
    BY_CLIENT_COUNT = "by_client_count"


class AggregationKind(StrEnum):
    MEAN = "mean"
    STANDARD_DEVIATION = "standard_deviation"
    COEFFICIENT_OF_VARIATION = "coefficient_of_variation"
    QUANTILE = "quantile"
    INTERQUARTILE_RANGE = "interquartile_range"
    RANGE = "range"
    MAXIMUM = "maximum"
    JAIN_INDEX = "jain_index"
    GINI_COEFFICIENT = "gini_coefficient"


class PrecisionComputation(StrEnum):
    FLOAT64 = "float64"


class RoundingMode(StrEnum):
    NONE = "none"
    HALF_EVEN = "half_even"


class HistogramRangeMode(StrEnum):
    POOLED_MIN_MAX = "pooled_min_max"


class HistogramEdgeMode(StrEnum):
    SHARED_ACROSS_CLIENTS = "shared_across_clients"


class EmptyBinPolicy(StrEnum):
    ZERO_PROBABILITY = "zero_probability"


class PairwiseAggregationMode(StrEnum):
    MEAN_UNORDERED_PAIRS = "mean_unordered_pairs"


class MetricId(StrEnum):
    FALSE_POSITIVE_RATE = "false_positive_rate"
    TRUE_POSITIVE_RATE = "true_positive_rate"
    BALANCED_ACCURACY = "balanced_accuracy"
    MACRO_F1 = "macro_f1"
    AUROC = "auroc"

    MEAN_FPR = "mean_fpr"
    STANDARD_DEVIATION_FPR = "standard_deviation_fpr"
    CV_FPR = "cv_fpr"
    CV_TPR = "cv_tpr"
    IQR_FPR = "iqr_fpr"
    FPR_RANGE = "fpr_range"
    WORST_CLIENT_FPR = "worst_client_fpr"
    P10_MACRO_F1 = "p10_macro_f1"
    WORST_CLIENT_BALANCED_ACCURACY = "worst_client_balanced_accuracy"
    JAIN_INDEX = "jain_index"
    GINI_COEFFICIENT = "gini_coefficient"

    ABSOLUTE_THRESHOLD_ERROR = "absolute_threshold_error"
    RELATIVE_THRESHOLD_ERROR = "relative_threshold_error"
    TARGET_EXCEEDANCE = "target_exceedance"
    SIGNED_ATTAINMENT_ERROR = "signed_attainment_error"
    ABSOLUTE_ATTAINMENT_ERROR = "absolute_attainment_error"
    THRESHOLD_DISPERSION = "threshold_dispersion"
    THRESHOLD_VARIANCE_ACROSS_REPLICATES = "threshold_variance_across_replicates"

    PAIRWISE_JS_DIVERGENCE = "pairwise_js_divergence"
    ADJUSTED_RAND_INDEX = "adjusted_rand_index"
    WITHIN_CLUSTER_DISPERSION = "within_cluster_dispersion"
    ACROSS_CLUSTER_DISPERSION = "across_cluster_dispersion"


class ResultRecordType(StrEnum):
    CLIENT_METRICS = "client_metrics"
    CLIENT_ELIGIBILITY = "client_eligibility"
    CROSS_CLIENT_METRICS = "cross_client_metrics"


class EvaluationArtifactKey(StrEnum):
    THRESHOLDS = "thresholds"
    TEST_SCORES = "test_scores"
    CLIENT_METRICS = "client_metrics"


class EvaluationColumn(StrEnum):
    CLIENT_ID = "client_id"
    SCORE = "score"
    LABEL = "label"
    THRESHOLD = "threshold"

    TRUE_POSITIVES = "true_positives"
    FALSE_POSITIVES = "false_positives"
    TRUE_NEGATIVES = "true_negatives"
    FALSE_NEGATIVES = "false_negatives"

    FALSE_POSITIVE_RATE = "false_positive_rate"
    FALSE_POSITIVE_RATE_STATUS = "false_positive_rate_status"
    TRUE_POSITIVE_RATE = "true_positive_rate"
    TRUE_POSITIVE_RATE_STATUS = "true_positive_rate_status"
    BALANCED_ACCURACY = "balanced_accuracy"
    BALANCED_ACCURACY_STATUS = "balanced_accuracy_status"
    MACRO_F1 = "macro_f1"
    MACRO_F1_STATUS = "macro_f1_status"
    AUROC = "auroc"
    AUROC_STATUS = "auroc_status"

    POLICY_ID = "policy_id"
    SEED = "seed"