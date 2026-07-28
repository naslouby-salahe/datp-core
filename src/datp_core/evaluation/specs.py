"""Strict evaluation configuration models."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveFloat,
    PositiveInt,
    model_validator,
)

from datp_core.core.identifiers import MetricBundleId
from datp_core.evaluation.enums import (
    AggregationKind,
    EmptyBinPolicy,
    HistogramEdgeMode,
    HistogramRangeMode,
    MetricDirection,
    MetricId,
    MetricRequirement,
    MetricRole,
    MetricStatus,
    MetricUnit,
    MissingClassPolicy,
    PairwiseAggregationMode,
    PrecisionComputation,
    PredictionRule,
    QuantileEstimator,
    ResultRecordType,
    RoundingMode,
    WeightingMode,
    ZeroDenominatorPolicy,
)


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
    )


class MetricDefinition(StrictFrozenModel):
    identifier: MetricId
    formula: str
    unit: MetricUnit
    direction: MetricDirection
    role: MetricRole
    requirements: tuple[MetricRequirement, ...] = ()


class AggregateMetricDefinition(StrictFrozenModel):
    identifier: MetricId
    source_metric: MetricId
    aggregation: AggregationKind
    unit: MetricUnit
    direction: MetricDirection
    role: MetricRole
    quantile: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_quantile(self) -> Self:
        uses_quantile = self.aggregation is AggregationKind.QUANTILE
        has_quantile = self.quantile is not None

        if uses_quantile != has_quantile:
            raise ValueError("quantile is required only for quantile aggregation")

        return self


class CrossClientAggregationSpec(StrictFrozenModel):
    standard_deviation_ddof: int = Field(ge=0)
    cv_instability_threshold_factor: PositiveFloat
    minimum_client_count: PositiveInt
    weighting: WeightingMode
    quantile_estimator: QuantileEstimator
    metrics: tuple[AggregateMetricDefinition, ...]

    @model_validator(mode="after")
    def validate_unique_metrics(self) -> Self:
        identifiers = tuple(metric.identifier for metric in self.metrics)

        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Cross-client metric identifiers must be unique")

        return self


class JsDivergenceSpec(StrictFrozenModel):
    histogram_bins: PositiveInt
    logarithm_base: int = Field(ge=2)
    range_mode: HistogramRangeMode
    edge_mode: HistogramEdgeMode
    empty_bin_policy: EmptyBinPolicy
    pairwise_aggregation: PairwiseAggregationMode
    minimum_client_count: PositiveInt


class PrecisionPolicySpec(StrictFrozenModel):
    computation: PrecisionComputation
    rounding: RoundingMode


class MetricDefinitions(StrictFrozenModel):
    prediction_rule: PredictionRule
    per_client_before_aggregation: bool
    test_rows_only: bool
    metrics: tuple[MetricDefinition, ...]
    cross_client_aggregation: CrossClientAggregationSpec
    js_divergence: JsDivergenceSpec
    precision_policy: PrecisionPolicySpec
    metric_statuses: tuple[MetricStatus, ...]
    forbidden_substitutions: tuple[str, ...]

    @model_validator(mode="after")
    def validate_definition_set(self) -> Self:
        identifiers = tuple(metric.identifier for metric in self.metrics)

        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Metric identifiers must be unique")

        required = (
            MetricId.FALSE_POSITIVE_RATE,
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BALANCED_ACCURACY,
            MetricId.MACRO_F1,
            MetricId.AUROC,
        )

        missing = tuple(identifier for identifier in required if identifier not in identifiers)

        if missing:
            raise ValueError(f"Missing required metric definitions: {[item.value for item in missing]}")

        auroc = next(metric for metric in self.metrics if metric.identifier is MetricId.AUROC)

        if auroc.role is not MetricRole.MODEL_QUALITY_CONTROL:
            raise ValueError("AUROC must be configured as a model-quality control")

        if MetricRequirement.BOTH_CLASSES not in auroc.requirements:
            raise ValueError("AUROC must require both classes")

        return self


class MetricBundleSpec(StrictFrozenModel):
    identifier: MetricBundleId
    metrics: tuple[MetricId, ...]
    cross_client_metrics: tuple[MetricId, ...] = ()
    primary_dispersion_metric: MetricId
    model_quality_control: MetricId
    excludes_ineligible_clients: bool
    requires_attack_evaluable_clients: bool

    @model_validator(mode="after")
    def validate_bundle_references(self) -> Self:
        if self.primary_dispersion_metric not in self.cross_client_metrics:
            raise ValueError("Primary dispersion metric must be a cross-client metric")

        if self.model_quality_control not in self.metrics:
            raise ValueError("Model-quality control must be included in per-client metrics")

        return self


class EvaluationResultContract(StrictFrozenModel):
    per_evaluation_result_type: ResultRecordType
    per_evaluation_eligibility_result_type: ResultRecordType
    required_records: tuple[ResultRecordType, ...]

    @model_validator(mode="after")
    def validate_required_records(self) -> Self:
        required = (
            self.per_evaluation_result_type,
            self.per_evaluation_eligibility_result_type,
        )

        missing = tuple(record for record in required if record not in self.required_records)

        if missing:
            raise ValueError(f"Required record types are incomplete: {[item.value for item in missing]}")

        return self


class ClusterDiagnosticSpec(StrictFrozenModel):
    adjusted_rand_index: ScalarMetricSpec
    within_cluster_dispersion: DispersionMetricSpec
    across_cluster_dispersion: DispersionMetricSpec


class DispersionMetricSpec(StrictFrozenModel):
    """FPR range, worst-client FPR, worst-client BA — extremal metrics."""

    kind: Literal["dispersion"] = "dispersion"
    formula: str | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None


class HeterogeneityDiagnosticSpec(StrictFrozenModel):
    pairwise_js_divergence: JsDivergenceSpec


class InvariantMetricSpec(StrictFrozenModel):
    """AUROC — threshold-independent model-quality control."""

    kind: Literal["invariant"] = "invariant"
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None
    requires_both_classes: bool | None = None
    role: MetricRole | None = None
    invariance_check: str | None = None


# -- Aggregation and diagnostics specs -------------------------------------


class QuantileMetricSpec(StrictFrozenModel):
    """IQR FPR, p10 macro F1 — quantile-based metrics."""

    kind: Literal["quantile"] = "quantile"
    formula: str | None = None
    quantile_estimator: QuantileEstimator | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None


class RatioMetricSpec(StrictFrozenModel):
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


class ScalarMetricSpec(StrictFrozenModel):
    """FPR, TPR — ratio of counts with denominator behavior."""

    kind: Literal["scalar"] = "scalar"
    formula: str | None = None
    unit: MetricUnit | None = None
    direction: MetricDirection | None = None
    zero_denominator: ZeroDenominatorPolicy | None = None
    requires: tuple[str, ...] | None = None
    missing_class_behavior: MissingClassPolicy | None = None


class ThresholdEstimationSpec(StrictFrozenModel):
    absolute_threshold_error: ScalarMetricSpec
    relative_threshold_error: RatioMetricSpec
    oracle_definition: str
    target_exceedance: ScalarMetricSpec
    signed_attainment_error: ScalarMetricSpec
    absolute_attainment_error: ScalarMetricSpec
    threshold_dispersion: RatioMetricSpec
    threshold_variance_across_replicates: RatioMetricSpec


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


# -- Metric specifications (discriminated) ----------------------------------

ScalarMetricSpec.model_rebuild()
RatioMetricSpec.model_rebuild()
QuantileMetricSpec.model_rebuild()
InvariantMetricSpec.model_rebuild()
DispersionMetricSpec.model_rebuild()
