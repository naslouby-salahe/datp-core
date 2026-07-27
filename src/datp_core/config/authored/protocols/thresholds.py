"""Authored threshold policy contracts: the closed threshold-policy discriminated union,
quantile estimators, and cross-policy defaults (protocols.yaml)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from datp_core.config.authored.base import StrictFrozenConfigModel


class ClientMessageConfig(StrictFrozenConfigModel):
    fields: list[str]
    variance_convention: str
    raw_scores_transmitted: bool
    attack_labels_transmitted: bool


class QuantileEstimatorConfig(StrictFrozenConfigModel):
    sort_order: str
    index_formula: str
    interpolation: str
    single_element_behavior: str
    empty_input_behavior: str
    non_finite_input_behavior: str
    tie_behavior: str


class BaseThresholdPolicyConfig(StrictFrozenConfigModel):
    quantile: float = Field(ge=0.0, le=1.0)
    quantile_estimator: str


class SharedMeanThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["shared_threshold"]
    construction: Literal["mean"]
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: Literal["none"]
    client_accumulation_order: str
    threshold_ownership: str


class SharedPooledThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["shared_threshold"]
    construction: Literal["pooled"]
    aggregation_scope: str
    aggregation_formula: str
    concatenation_order: str
    sample_weighting: str
    threshold_ownership: str


class SharedWeightedThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["shared_threshold"]
    construction: Literal["weighted"]
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    client_accumulation_order: str
    zero_total_weight_behavior: str
    threshold_ownership: str


class LocalQuantileThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["local_threshold"]
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    threshold_ownership: str


class FamilyMeanThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["family_threshold"]
    requires_capability: str
    taxonomy_source: str
    aggregated_quantity: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    client_accumulation_order: str
    singleton_family_behavior: str
    family_with_no_eligible_member_behavior: str
    client_without_family_label_behavior: str
    unavailable_without_taxonomy: str
    threshold_ownership: str


class CentralizedPooledThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["centralized_pooled_threshold"]
    source_score_population: str
    aggregation_scope: str
    aggregation_formula: str
    concatenation_order: str
    sample_weighting: str
    provenance_separation: str
    threshold_ownership: str


class ClusterThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["cluster_threshold"]
    canonical: bool | None = None
    exploratory: bool | None = None
    aggregation: str
    cluster_count: int = Field(ge=1)
    aggregated_quantity: str
    aggregation_formula: str
    median_estimator: str | None = None
    sample_weighting: str
    client_accumulation_order: str
    fingerprint_features: list[str]
    fingerprint_estimators: dict[str, str]
    fingerprint_degenerate_client_rules: dict[str, float | dict[str, float]]
    fingerprint_non_finite_value_behavior: str
    standardization: dict[str, str | int]
    client_ordering_before_fit: str
    clustering: dict[str, str | int | float]
    label_canonicalization: str
    insufficient_eligible_clients_behavior: str
    degenerate_fingerprint_matrix_behavior: str
    required_diagnostics: list[str]
    threshold_ownership: str

    @model_validator(mode="after")
    def validate_canonical_cluster_policy(self) -> ClusterThresholdPolicyConfig:
        if self.canonical is True and self.cluster_count != 3:
            raise ValueError("The canonical B4 policy must use cluster_count=3")
        if self.canonical is True and self.exploratory is True:
            raise ValueError("A canonical B4 policy cannot also be exploratory")
        return self


class SplitConformalThresholdPolicyConfig(StrictFrozenConfigModel):
    policy: Literal["conformal_local_threshold"]
    conformal_mode: str
    coverage_alpha: float
    nominal_coverage: float
    target_exceedance: float
    rank_formula: str
    order_statistic_selection: str
    interpolation: str
    tie_break: str
    finite_sample_attainability_rule: str
    unattainable_behavior: str
    minimum_sample_count: int
    calibration_unit: str
    calibration_scope: str
    evaluation_unit: str
    coverage_breakdown: list[str]
    coverage_target_error: str
    output_type: str
    exchangeability_limitation: str
    unavailable_behavior: str
    threshold_ownership: str


class LocalGlobalShrinkagePolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["local_global_shrinkage_threshold"]
    local_reference: str
    global_reference: str
    interpolation_formula: str
    weight_semantics: str
    weight_scope: str
    permitted_weight_range: dict[str, float]
    shrinkage_weight_grid: list[float]
    shrinkage_weight: float | None = None
    shrinkage_weight_resolution: str
    out_of_range_weight_behavior: str
    effective_lambda_reporting: str
    threshold_ownership: str

    @model_validator(mode="after")
    def validate_shrinkage_weights(self) -> LocalGlobalShrinkagePolicyConfig:
        lower = self.permitted_weight_range.get("minimum")
        upper = self.permitted_weight_range.get("maximum")
        if lower is None or upper is None or lower > upper:
            raise ValueError("permitted_weight_range requires ordered minimum and maximum values")
        values = (*self.shrinkage_weight_grid, self.shrinkage_weight)
        if any(value is not None and not lower <= value <= upper for value in values):
            raise ValueError("shrinkage weights must fall within permitted_weight_range")
        return self


class CalibrationFallbackPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["calibration_size_aware_fallback_threshold"]
    local_reference: str
    global_reference: str
    interpolation_formula: str
    weight_semantics: str
    weight_scope: str
    weight_formula: str
    weight_formula_constants: dict[str, int]
    weight_monotone_in_calibration_count: bool
    clamping: str
    permitted_weight_range: dict[str, float]
    zero_calibration_behavior: str
    minimum_calibration_behavior: str
    effective_lambda_reporting: str
    fallback_frequency_reporting: str
    threshold_ownership: str


class FederatedMatchedExceedancePolicyConfig(StrictFrozenConfigModel):
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["matched_exceedance"]
    quantile: float = Field(ge=0.0, le=1.0)
    primary_comparator: bool
    client_message: ClientMessageConfig
    global_mean_formula: str
    within_term_formula: str
    between_term_formula: str
    pooled_variance_formula: str
    between_term_mandatory: bool
    between_ratio_formula: str
    between_ratio_zero_denominator_behavior: str
    global_standard_deviation_formula: str
    client_accumulation_order: str
    zero_total_count_behavior: str
    candidate_grid: dict[str, str | float | bool]
    exceedance_exchange: dict[str, list[str] | str]
    selection: dict[str, str]
    required_diagnostics: list[str]
    threshold_ownership: str


class FederatedFixedCoefficientPolicyConfig(StrictFrozenConfigModel):
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["fixed_k"]
    quantile: float = Field(ge=0.0, le=1.0)
    primary_comparator: bool
    supplementary_sensitivity_only: bool
    client_message: ClientMessageConfig
    global_mean_formula: str
    within_term_formula: str
    between_term_formula: str
    pooled_variance_formula: str
    between_term_mandatory: bool
    between_ratio_formula: str
    between_ratio_zero_denominator_behavior: str
    global_standard_deviation_formula: str
    client_accumulation_order: str
    zero_total_count_behavior: str
    threshold_formula: str
    fixed_k_grid: list[float]
    fixed_k: float | None = None
    fixed_k_resolution: str
    required_diagnostics: list[str]
    threshold_ownership: str


TypedThresholdPolicyConfig = (
    SharedMeanThresholdPolicyConfig
    | SharedPooledThresholdPolicyConfig
    | SharedWeightedThresholdPolicyConfig
    | LocalQuantileThresholdPolicyConfig
    | FamilyMeanThresholdPolicyConfig
    | CentralizedPooledThresholdPolicyConfig
    | ClusterThresholdPolicyConfig
    | SplitConformalThresholdPolicyConfig
    | LocalGlobalShrinkagePolicyConfig
    | CalibrationFallbackPolicyConfig
    | FederatedMatchedExceedancePolicyConfig
    | FederatedFixedCoefficientPolicyConfig
)


class ThresholdPolicyDefaultsConfig(StrictFrozenConfigModel):
    source_score_population: str
    eligibility_filter: str
    attack_rows_forbidden_in_calibration: bool
    non_finite_calibration_score: str
    empty_client_calibration: str
    application_scope: str
    required_diagnostic_fields: list[str]
