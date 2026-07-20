"""Pydantic 2 models for authored protocols configuration (protocols.yaml)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThresholdPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    policy: str
    quantile: float | None = Field(default=0.95, ge=0.0, le=1.0)
    construction: str | None = None
    quantile_estimator: str | None = None
    aggregation_scope: str | None = None
    aggregation_formula: str | None = None
    sample_weighting: str | None = None
    client_accumulation_order: str | None = None
    threshold_ownership: str | None = None
    concatenation_order: str | None = None
    zero_total_weight_behavior: str | None = None
    requires_capability: str | None = None
    taxonomy_source: str | None = None
    aggregated_quantity: str | None = None
    singleton_family_behavior: str | None = None
    family_with_no_eligible_member_behavior: str | None = None
    client_without_family_label_behavior: str | None = None
    unavailable_without_taxonomy: str | None = None
    source_score_population: str | None = None
    provenance_separation: str | None = None
    canonical: bool | None = None
    exploratory: bool | None = None
    aggregation: str | None = None
    cluster_count: int | None = None
    fingerprint_features: list[str] | None = None
    fingerprint_estimators: dict[str, str] | None = None
    fingerprint_degenerate_client_rules: dict[str, Any] | None = None
    fingerprint_non_finite_value_behavior: str | None = None
    standardization: dict[str, Any] | None = None
    client_ordering_before_fit: str | None = None
    clustering: dict[str, Any] | None = None
    label_canonicalization: str | None = None
    insufficient_eligible_clients_behavior: str | None = None
    degenerate_fingerprint_matrix_behavior: str | None = None
    required_diagnostics: list[str] | None = None
    median_estimator: str | None = None
    conformal_mode: str | None = None
    coverage_alpha: float | None = None
    nominal_coverage: float | None = None
    target_exceedance: float | None = None
    rank_formula: str | None = None
    order_statistic_selection: str | None = None
    interpolation: str | None = None
    tie_break: str | None = None
    finite_sample_attainability_rule: str | None = None
    unattainable_behavior: str | None = None
    minimum_sample_count: int | None = None
    calibration_unit: str | None = None
    calibration_scope: str | None = None
    evaluation_unit: str | None = None
    coverage_breakdown: list[str] | None = None
    coverage_target_error: str | None = None
    output_type: str | None = None
    exchangeability_limitation: str | None = None
    unavailable_behavior: str | None = None
    local_reference: str | None = None
    global_reference: str | None = None
    interpolation_formula: str | None = None
    weight_semantics: str | None = None
    weight_scope: str | None = None
    permitted_weight_range: dict[str, float] | None = None
    shrinkage_weight_grid: list[float] | None = None
    shrinkage_weight: float | None = None
    shrinkage_weight_resolution: str | None = None
    out_of_range_weight_behavior: str | None = None
    effective_lambda_reporting: str | None = None
    weight_formula: str | None = None
    weight_formula_constants: dict[str, Any] | None = None
    weight_monotone_in_calibration_count: bool | None = None
    clamping: str | None = None
    zero_calibration_behavior: str | None = None
    minimum_calibration_behavior: str | None = None
    fallback_frequency_reporting: str | None = None
    mode: str | None = None
    primary_comparator: bool | None = None
    client_message: dict[str, Any] | None = None
    global_mean_formula: str | None = None
    within_term_formula: str | None = None
    between_term_formula: str | None = None
    pooled_variance_formula: str | None = None
    between_term_mandatory: bool | None = None
    between_ratio_formula: str | None = None
    between_ratio_zero_denominator_behavior: str | None = None
    global_standard_deviation_formula: str | None = None
    zero_total_count_behavior: str | None = None
    candidate_grid: dict[str, Any] | None = None
    exceedance_exchange: dict[str, Any] | None = None
    selection: dict[str, Any] | None = None
    supplementary_sensitivity_only: bool | None = None
    threshold_formula: str | None = None
    fixed_k_grid: list[float] | None = None
    fixed_k: float | None = None
    fixed_k_resolution: str | None = None


class AuthoredProtocolsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    schema_version: int = Field(ge=1)
    model_architectures: dict[str, Any]
    optimizers: dict[str, Any]
    batching: dict[str, Any]
    determinism: dict[str, Any]
    seed_cohorts: dict[str, Any]
    checkpoint_profiles: dict[str, Any]
    training_profiles: dict[str, Any]
    eligibility_policies: dict[str, Any]
    normalization_strategies: dict[str, Any]
    quantile_estimators: dict[str, Any]
    threshold_policies: dict[str, ThresholdPolicyConfig]
    metric_definitions: dict[str, Any]
    metric_bundles: dict[str, Any]
    statistical_profiles: dict[str, Any]
    report_profiles: dict[str, Any]
    communication_estimation: dict[str, Any] | None = None

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"Unsupported protocols schema version: {value}")
        return value
