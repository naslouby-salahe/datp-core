"""Strict frozen Pydantic v2 configuration and serialization-boundary models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import MetricBundleId
from datp_core.evaluation.enums import (
    MetricDirection,
    MetricRole,
    MetricUnit,
    MissingClassPolicy,
    QuantileEstimator,
    WeightingMode,
    ZeroDenominatorPolicy,
)

# -- Base ------------------------------------------------------------------


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


# -- Metric specifications (discriminated) ----------------------------------


class ScalarMetricSpec(_StrictFrozenModel):
    """FPR, TPR — ratio of counts with denominator behavior."""

    kind: Literal["scalar"] = "scalar"
    formula: str | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None
    zero_denominator: ZeroDenominatorPolicy | None = None
    requires: tuple[str, ...] | None = None
    missing_class_behavior: MissingClassPolicy | None = None


class RatioMetricSpec(_StrictFrozenModel):
    """CV(FPR), CV(TPR), Jain index, Gini — derived ratio metrics."""

    kind: Literal["ratio"] = "ratio"
    formula: str | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None
    weighting: WeightingMode | None = None
    denominator_stabilizer: str | None = None
    zero_mean_behavior: ZeroDenominatorPolicy | None = None
    near_zero_mean_threshold_formula: str | None = None
    near_zero_mean_threshold_factor: float | None = None
    near_zero_mean_behavior: ZeroDenominatorPolicy | None = None
    minimum_client_count: int | None = None
    zero_sum_behavior: ZeroDenominatorPolicy | None = None


class QuantileMetricSpec(_StrictFrozenModel):
    """IQR FPR, p10 macro F1 — quantile-based metrics."""

    kind: Literal["quantile"] = "quantile"
    formula: str | None = None
    quantile_estimator: QuantileEstimator | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None


class DispersionMetricSpec(_StrictFrozenModel):
    """FPR range, worst-client FPR, worst-client BA — extremal metrics."""

    kind: Literal["dispersion"] = "dispersion"
    formula: str | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None


class InvariantMetricSpec(_StrictFrozenModel):
    """AUROC — threshold-independent model-quality control."""

    kind: Literal["invariant"] = "invariant"
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None
    requires_both_classes: bool | None = None
    role: MetricRole | None = None
    invariance_check: str | None = None


# -- Aggregation and diagnostics specs -------------------------------------


class CrossClientAggregationSpec(_StrictFrozenModel):
    mean_fpr: ScalarMetricSpec
    standard_deviation_ddof: int
    cv_fpr: RatioMetricSpec
    cv_tpr: RatioMetricSpec
    iqr_fpr: QuantileMetricSpec
    fpr_range: DispersionMetricSpec
    worst_client_fpr: DispersionMetricSpec
    p10_macro_f1: QuantileMetricSpec
    worst_client_ba: DispersionMetricSpec
    jain_index: RatioMetricSpec
    gini_coefficient: RatioMetricSpec


class ThresholdEstimationSpec(_StrictFrozenModel):
    absolute_threshold_error: ScalarMetricSpec
    relative_threshold_error: RatioMetricSpec
    oracle_definition: str
    target_exceedance: ScalarMetricSpec
    signed_attainment_error: ScalarMetricSpec
    absolute_attainment_error: ScalarMetricSpec
    threshold_dispersion: RatioMetricSpec
    threshold_variance_across_replicates: RatioMetricSpec


class JsDivergenceSpec(_StrictFrozenModel):
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


class HeterogeneityDiagnosticSpec(_StrictFrozenModel):
    pairwise_js_divergence: JsDivergenceSpec


class ClusterDiagnosticSpec(_StrictFrozenModel):
    adjusted_rand_index: ScalarMetricSpec
    within_cluster_dispersion: DispersionMetricSpec
    across_cluster_dispersion: DispersionMetricSpec


class PrecisionPolicySpec(_StrictFrozenModel):
    computation: str
    rounding: str


# -- Top-level definition records ------------------------------------------


class MetricDefinitions(_StrictFrozenModel):
    prediction_rule: str
    per_client_before_aggregation: bool
    test_rows_only: bool
    fpr: ScalarMetricSpec
    tpr: ScalarMetricSpec
    balanced_accuracy: ScalarMetricSpec
    macro_f1: ScalarMetricSpec
    auroc: InvariantMetricSpec
    cross_client_aggregation: CrossClientAggregationSpec
    threshold_estimation: ThresholdEstimationSpec
    heterogeneity_diagnostics: HeterogeneityDiagnosticSpec
    cluster_diagnostics: ClusterDiagnosticSpec
    precision_policy: PrecisionPolicySpec
    metric_statuses: tuple[str, ...]
    forbidden_substitutions: tuple[str, ...]


class MetricBundleSpec(_StrictFrozenModel):
    identifier: MetricBundleId
    metrics: tuple[str, ...]
    cross_client_aggregation: str | None = None
    primary_dispersion_metric: str | None = None
    model_quality_control: str | None = None
    excludes_ineligible_clients: bool | None = None
    requires_attack_evaluable_clients: bool | None = None


class EvaluationResultContract(_StrictFrozenModel):
    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: tuple[str, ...]
