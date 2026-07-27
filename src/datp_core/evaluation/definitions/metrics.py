"""Metric formula records — configured definitions, not computed values."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MetricFormulaRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class CrossClientAggregationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class ThresholdEstimationMetricsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    absolute_threshold_error: MetricFormulaRecord
    relative_threshold_error: MetricFormulaRecord
    oracle_definition: str
    target_exceedance: MetricFormulaRecord
    signed_attainment_error: MetricFormulaRecord
    absolute_attainment_error: MetricFormulaRecord
    threshold_dispersion: MetricFormulaRecord
    threshold_variance_across_replicates: MetricFormulaRecord


class JsDivergenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class HeterogeneityDiagnosticsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    pairwise_js_divergence: JsDivergenceRecord


class ClusterDiagnosticsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    adjusted_rand_index: MetricFormulaRecord
    within_cluster_dispersion: MetricFormulaRecord
    across_cluster_dispersion: MetricFormulaRecord


class PrecisionPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    computation: str
    rounding: str


class MetricDefinitionsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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
