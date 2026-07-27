"""Canonical analysis enums — single source of truth for every closed string vocabulary.

Reuses existing enums where concept ownership already exists. Adding an analysis
capability must not introduce raw string comparisons for any field listed here.
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Metric identifiers
# ---------------------------------------------------------------------------


class MetricIdentifier(StrEnum):
    """Primary metric names recognised across analysis capabilities."""

    CV_FPR = "cv_fpr"
    PAIRWISE_JS_DIVERGENCE = "pairwise_js_divergence"
    CV_FPR_DELTA = "cv_fpr_delta"


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class CoverageStatus(StrEnum):
    """Per-client coverage availability."""

    AVAILABLE = "available"
    UNAVAILABLE_NO_BENIGN_TEST_RECORDS = "unavailable_no_benign_test_records"


class CoverageDirection(StrEnum):
    """Coverage direction specification."""

    TWO_SIDED = "two_sided"
    UPPER = "upper"
    LOWER = "lower"


# ---------------------------------------------------------------------------
# Hypothesis testing
# ---------------------------------------------------------------------------


class AlternativeHypothesis(StrEnum):
    """Statistical alternative hypothesis."""

    TWO_SIDED = "two-sided"
    GREATER = "greater"
    LESS = "less"


class HypothesisTestName(StrEnum):
    """Named statistical tests used in result records."""

    WILCOXON_SIGNED_RANK = "wilcoxon_signed_rank"
    SPEARMAN_CORRELATION = "spearman_correlation"


# ---------------------------------------------------------------------------
# Confidence interval method
# ---------------------------------------------------------------------------


class ConfidenceIntervalMethod(StrEnum):
    """Method used to construct a confidence interval."""

    BCA_BOOTSTRAP = "BCa_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"


# ---------------------------------------------------------------------------
# Dispersion / clustering
# ---------------------------------------------------------------------------


class ClusterDispersionKind(StrEnum):
    """Direction of cluster dispersion comparison."""

    WITHIN = "within"
    ACROSS = "across"


class ClusterDispersionStatus(StrEnum):
    """Closed outcome of a within- or across-cluster dispersion computation."""

    AVAILABLE = "available"
    UNAVAILABLE_EMPTY_CLUSTER = "unavailable_empty_cluster"
    UNAVAILABLE_NO_AVAILABLE_FPR = "unavailable_no_available_fpr"
    UNAVAILABLE_INSUFFICIENT_OBSERVATIONS = "unavailable_insufficient_observations"
    UNAVAILABLE_INCOMPLETE_METRIC_POPULATION = "unavailable_incomplete_metric_population"
    UNAVAILABLE_NON_FINITE_INPUT = "unavailable_non_finite_input"


# ---------------------------------------------------------------------------
# Temporal recovery & chronology
# ---------------------------------------------------------------------------


class TemporalOutcomeBand(StrEnum):
    """Categorical outcome band for temporal-recovery analyses."""

    NO_MEANINGFUL_DEGRADATION = "no_meaningful_degradation"
    MEANINGFUL_RECOVERY = "meaningful_recovery"
    INSUFFICIENT_RECOVERY = "insufficient_recovery"


class NegativeRecoveryBehavior(StrEnum):
    """Policy for handling negative-recovery scenarios."""

    CLAMP_TO_ZERO = "clamp_to_zero"
    REPORT_NEGATIVE = "report_negative"


class ChronologyPolicy(StrEnum):
    """Policy for verifying chronology of temporal evaluations."""

    STRICT_VERIFICATION = "strict_verification"
    ALLOW_UNVERIFIABLE = "allow_unverifiable"


# ---------------------------------------------------------------------------
# Operational / resource
# ---------------------------------------------------------------------------


class AlertBurdenStatus(StrEnum):
    """Status of alert-burden availability."""

    AVAILABLE = "available"
    UNAVAILABLE_NO_CONFIGURED_RATES = "unavailable_no_configured_rates"


class ResourceEstimateBasis(StrEnum):
    """Basis for resource-cost estimation."""

    COMMUNICATION_CONTRACT = "communication_contract"
    EMPIRICAL_MEASUREMENT = "empirical_measurement"


# ---------------------------------------------------------------------------
# Ratio / effect
# ---------------------------------------------------------------------------


class FormulaIdentifier(StrEnum):
    """Canonical formula identifiers for ratio and derived-metric analyses."""

    CV_FPR_NEAR_ZERO_THRESHOLD = "0.10 * (1 - evaluated_threshold_policy_quantile)"


class UndefinedDenominatorBehavior(StrEnum):
    """Behaviour when a ratio denominator is undefined or zero."""

    SKIP = "skip"
    FAIL = "fail"
    ZERO_RESULT = "zero_result"


class DenominatorComposition(StrEnum):
    """How a ratio denominator is constructed."""

    SHARED_MEAN = "shared_mean"
    LOCAL = "local"
    GAP = "shared_minus_local_gap_of_the_same_seed"


class MaterialityRuleKind(StrEnum):
    """Kind of materiality rule for ratio analyses."""

    REQUIRED_FROM_BINDING_ANALYSIS = "required_from_the_binding_analysis"
    CONFIGURED_THRESHOLD = "configured_threshold"


# ---------------------------------------------------------------------------
# Anchor equivalence
# ---------------------------------------------------------------------------


class AnchorComparisonMode(StrEnum):
    """Comparison mode for anchor-equivalence validation."""

    STATISTICAL_FALLBACK = "statistical_fallback"


class AnchorCheckIdentifier(StrEnum):
    """Named checks within anchor-equivalence validation."""

    POSITIVE_REPRODUCED_DELTA = "positive_reproduced_delta"
    REPRODUCED_ESTIMATE_WITHIN_HISTORICAL_INTERVAL = "reproduced_estimate_within_historical_interval"
    OVERLAPPING_CONFIDENCE_INTERVALS = "overlapping_confidence_intervals"
    NO_MATERIAL_MOVEMENT_TOWARD_ZERO = "no_material_movement_toward_zero"
    REPRODUCED_INTERVAL_WIDTH = "reproduced_interval_width_at_most_1.20x_historical_width"
    VERIFIED_CONFIGURATION_AND_PROVENANCE = "verified_configuration_and_provenance"


# ---------------------------------------------------------------------------
# Sweep dimensions
# ---------------------------------------------------------------------------


class SweepDimensionKind(StrEnum):
    """Known sweep-dimension names."""

    CALIBRATION_SAMPLE_COUNT = "calibration_sample_count"
    THRESHOLD_QUANTILE = "threshold_quantile"
    SHRINKAGE_WEIGHT = "shrinkage_weight"
    FEDERATED_PROXIMAL_MU = "mu"
    DITTO_PROXIMAL_WEIGHT = "ditto_weight"
    PARTITION_CONDITION = "partition_condition"


# ---------------------------------------------------------------------------
# Operational inputs
# ---------------------------------------------------------------------------


class OperationalInputIdentifier(StrEnum):
    """Named operational inputs referenced by resource-cost analyses."""

    PARAMETERS = "parameters"
    ROUNDS = "rounds"
    CLIENT_COUNT = "client_count"


class CommunicationFieldIdentifier(StrEnum):
    """Fields referenced in threshold-communication estimates.

    Wire-level field names encode their data type as the suffix after the last
    underscore (``_float64``, ``_uint64``, ``_uint32``) for byte-width lookup.
    """

    THRESHOLD = "threshold"
    CLUSTER_LABEL = "cluster_label"
    CALIBRATION_SCORE = "calibration_score"
    LOCAL_QUANTILE = "local_quantile_float64"
    SHARED_THRESHOLD = "shared_threshold_float64"
    LOCAL_THRESHOLD = "local_threshold_float64"
    MEAN_ERROR = "mean_error_float64"
    STD_ERROR = "std_error_float64"
    SKEW_ERROR = "skew_error_float64"
    P95_ERROR = "p95_error_float64"
    CLUSTER_IDENTIFIER = "cluster_identifier_uint32"
    CLUSTER_THRESHOLD = "cluster_threshold_float64"
    BENIGN_CALIBRATION_COUNT = "benign_calibration_count_uint64"
    BENIGN_LOCAL_MEAN = "benign_local_mean_float64"
    BENIGN_LOCAL_VARIANCE = "benign_local_variance_float64"
    CANDIDATE_COEFFICIENT = "candidate_coefficient_float64"
    BENIGN_EXCEEDANCE_COUNT = "benign_exceedance_count_uint64"


# ---------------------------------------------------------------------------
# Units, fields, aggregations
# ---------------------------------------------------------------------------


class ComparisonUnit(StrEnum):
    """Unit of comparison across evaluations or seeds."""

    SEED = "seed"
    EVALUATION = "evaluation"
    PARTITION = "partition"
    CLIENT = "client"


class ProducedField(StrEnum):
    """Fields produced by multi-field analyses."""

    THRESHOLD = "threshold"
    EXCEEDANCE = "exceedance"
    SCORE = "score"
    COVERAGE = "coverage"
    DISPERSION = "dispersion"


class ReplicateAggregation(StrEnum):
    """Method for aggregating across replicates within a seed."""

    MEAN = "mean"
    MEDIAN = "median"


class InferentialUnit(StrEnum):
    """Unit of statistical inference."""

    SEED = "seed"
    CLIENT = "client"


# ---------------------------------------------------------------------------
# Artifact and result kinds
# ---------------------------------------------------------------------------


class ArtifactKind(StrEnum):
    """Kinds of artifacts consumed or produced by analysis capabilities."""

    THRESHOLD = "threshold"
    CALIBRATION_SCORE = "calibration_score"
    TEST_SCORE = "test_score"
    CLIENT_METRIC = "client_metric"
    CHECKPOINT = "checkpoint"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    STATISTICAL_RESULT = "statistical_result"
    PREREQUISITE_FROZEN_RESULT = "prerequisite_frozen_result"


class AnalysisResultKind(StrEnum):
    """One variant per result family — used for codec registry dispatch."""

    PAIRED_THRESHOLD = "paired_threshold_analysis_result"
    FEDERATED_PROXIMAL_SELECTION = "federated_proximal_selection_result"
    DITTO_SELECTION = "ditto_selection_result"
    METRIC_ASSOCIATION = "metric_association_analysis_result"
    THRESHOLD_STABILITY = "threshold_stability_analysis_result"
    RECOVERY_FRACTION = "recovery_fraction_analysis_result"
    ABSORPTION = "absorption_analysis_result"
    CONFORMAL_COVERAGE = "conformal_coverage_analysis_result"
    DISTRIBUTION_MECHANISM = "distribution_mechanism_analysis_result"
    DISTRIBUTION_TRADEOFF = "distribution_tradeoff_analysis_result"
    LOCKED_CLIENT_DISTRIBUTION = "locked_client_distribution_analysis_result"
    ALERT_BURDEN = "alert_burden_analysis_result"
    QUANTILE_ESTIMATION = "quantile_estimation_analysis_result"
    RESOURCE_COST = "resource_cost_analysis_result"
    CLUSTER_STABILITY = "cluster_stability_analysis_result"
    CLUSTER_ABLATION = "cluster_ablation_analysis_result"
    TEMPORAL_RECOVERY = "temporal_recovery_analysis_result"
    ANCHOR_EQUIVALENCE = "anchor_equivalence_analysis_result"
