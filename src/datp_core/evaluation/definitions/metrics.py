"""Metric formula records — configured definitions, not computed values."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class MetricFormulaRecord:
    formula: str | None
    unit: str | None
    direction: str | None
    zero_denominator: str | None
    requires: tuple[str, ...] | None
    missing_class_behavior: str | None
    requires_both_classes: bool | None
    role: str | None
    invariance_check: str | None
    quantile_estimator: str | None
    zero_sum_behavior: str | None
    zero_oracle_behavior: str | None
    zero_mean_behavior: str | None
    denominator_stabilizer: str | None
    near_zero_mean_threshold_formula: str | None
    near_zero_mean_behavior: str | None
    near_zero_mean_threshold_factor: float | None
    minimum_client_count: int | None
    weighting: str | None
    comparison_unit: str | None


@define(frozen=True, slots=True, kw_only=True)
class CrossClientAggregationRecord:
    mean_fpr: MetricFormulaRecord
    standard_deviation_ddof: int
    cv_fpr: MetricFormulaRecord
    cv_tpr: MetricFormulaRecord
    iqr_fpr: MetricFormulaRecord
    fpr_range: MetricFormulaRecord
    worst_client_fpr: MetricFormulaRecord
    p10_macro_f1: MetricFormulaRecord
    worst_client_ba: MetricFormulaRecord
    jain_index: MetricFormulaRecord
    gini_coefficient: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class ThresholdEstimationMetricsRecord:
    absolute_threshold_error: MetricFormulaRecord
    relative_threshold_error: MetricFormulaRecord
    oracle_definition: str
    target_exceedance: MetricFormulaRecord
    signed_attainment_error: MetricFormulaRecord
    absolute_attainment_error: MetricFormulaRecord
    threshold_dispersion: MetricFormulaRecord
    threshold_variance_across_replicates: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class JsDivergenceRecord:
    definition: str
    histogram_bins: int
    binning_range: str
    binning_edges: str
    logarithm_base: int
    empty_bin_handling: str
    pairwise_aggregation: str
    unit: str
    direction: str
    minimum_client_count: int


@define(frozen=True, slots=True, kw_only=True)
class HeterogeneityDiagnosticsRecord:
    pairwise_js_divergence: JsDivergenceRecord


@define(frozen=True, slots=True, kw_only=True)
class ClusterDiagnosticsRecord:
    adjusted_rand_index: MetricFormulaRecord
    within_cluster_dispersion: MetricFormulaRecord
    across_cluster_dispersion: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class PrecisionPolicyRecord:
    computation: str
    rounding: str


@define(frozen=True, slots=True, kw_only=True)
class MetricDefinitionsRecord:
    prediction_rule: str
    per_client_before_aggregation: bool
    test_rows_only: bool
    fpr: MetricFormulaRecord
    tpr: MetricFormulaRecord
    balanced_accuracy: MetricFormulaRecord
    macro_f1: MetricFormulaRecord
    auroc: MetricFormulaRecord
    cross_client_aggregation: CrossClientAggregationRecord
    threshold_estimation: ThresholdEstimationMetricsRecord
    heterogeneity_diagnostics: HeterogeneityDiagnosticsRecord
    cluster_diagnostics: ClusterDiagnosticsRecord
    precision_policy: PrecisionPolicyRecord
    metric_statuses: tuple[str, ...]
    forbidden_substitutions: tuple[str, ...]
