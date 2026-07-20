"""Strict Pydantic 2 models for authored protocols configuration (protocols.yaml)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator


class ModelInputDimensionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    resolution: str
    declared_per_dataset: bool
    validation: str


class ModelDecoderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    construction: str
    final_layer_output_dim: str


class ModelParameterInitializationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    weight: str
    bias: str
    applied_to: str
    seeded_by: str


class ModelAnomalyScoreConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    definition: str
    orientation: str


class ModelArchitectureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    kind: Literal["dense_autoencoder"]
    input_dimension: ModelInputDimensionConfig
    hidden_dims: list[int]
    bottleneck_dim: str
    decoder: ModelDecoderConfig
    activation: str
    activation_placement: str
    output_activation: str
    normalization_layers: str
    bias: bool
    parameter_initialization: ModelParameterInitializationConfig
    reconstruction_objective: str
    training_loss_reduction: str
    anomaly_score: ModelAnomalyScoreConfig
    precision: str


class OptimizerProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    optimizer_type: str
    learning_rate: float
    beta_1: float
    beta_2: float
    epsilon: float
    weight_decay: float
    amsgrad: bool
    scheduler: str
    gradient_clipping: str
    state_lifecycle: str
    state_aggregated_by_server: bool


class BatchingProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    micro_batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    shuffle_each_epoch: bool
    shuffle_unit: str
    incomplete_final_batch: str
    row_ordering_before_shuffle: str
    shuffle_seed_namespace: str
    worker_seed_namespace: str


class SeedNamespaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    key: str
    components: list[str]


class DeterminismProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    seed_domains: list[str]
    partition_seed_independent_of_training_seeds: bool
    checkpoint_selection_uses_no_stochastic_seed: bool
    derived_seed_algorithm: dict[str, str | int]
    seed_namespaces: dict[str, SeedNamespaceConfig]
    resolved_seeds_required_in_manifests: list[str]


class SeedCohortConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    paired_seed_count: int
    training_seeds: list[int]
    bootstrap_analysis_seed: int
    analysis_seed_model: str


class CheckpointSelectorInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    population: str
    quantity: str
    client_weighting: str | None = None
    aggregation_over_clients: str | None = None
    client_accumulation_order: str | None = None
    aggregation_over_rows: str | None = None


class CheckpointSelectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    rule: str
    selector_input: CheckpointSelectorInputConfig | None = None
    tie_break: str | None = None
    aggregation: str | None = None
    scope: str | None = None
    selected_round_reuse: str | None = None
    weights_remain_seed_and_population_specific: bool | None = None
    forbidden_selectors: list[str] | None = None
    selection_granularity: str | None = None


class CheckpointConvergenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    metric: str
    rounds_initial: int
    rule: str
    formula: str
    zero_start_loss_behavior: str
    tolerance: float
    window_rounds: int
    window: str
    qualification: str
    no_qualifying_round_behavior: str


class CheckpointProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    total_rounds: int | None = None
    total_epochs: int | None = None
    rounds: list[int] | None = None
    epochs: list[int] | None = None
    early_stopping: str
    convergence: CheckpointConvergenceConfig | None = None
    convergence_logged_without_stopping: bool | None = None
    checkpoint_save_policy: str | None = None
    selection: CheckpointSelectionConfig


class TrainingProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    kind: str
    model_architecture: str
    optimizer: str
    batching: str
    local_epochs: int | None = None
    participation: str | None = None
    participation_rule: str | None = None
    client_ordering: str | None = None
    client_update_weighting: str | None = None
    aggregation_formula: str | None = None
    aggregation_accumulation_order: str | None = None
    personalization: str | None = None
    checkpoint_authorization: str
    personalized_local_epochs: int | None = None
    personalization_proximal_weight: float | None = None
    personalization_parameter_grid: list[float] | None = None
    personalization_parameter_selection: dict[str, JsonValue] | None = None
    ditto_specification: dict[str, JsonValue] | None = None
    proximal_objective: str | None = None
    mu: float | None = None
    mu_grid: list[float] | None = None
    mu_resolution: str | None = None
    mu_zero_forbidden_as_a_fedprox_condition: bool | None = None
    training_population: str | None = None
    row_ordering_before_shuffle: str | None = None
    validation_split: dict[str, JsonValue] | None = None
    federation: FederationStrategyConfig | None = None


class FederationStrategyConfig(BaseModel):
    """Authored Flower FedAvg participation contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: int
    minimum_evaluate_clients: int
    minimum_available_clients: int


class EligibilityPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    minimum_benign_calibration_count: int
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: list[str]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: dict[str, str | bool]
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None = None
    permitted_use: str | None = None


class NormalizationStrategyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    formula: str
    fitted_statistics: list[str]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None = None


class QuantileEstimatorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    sort_order: str
    index_formula: str
    interpolation: str
    single_element_behavior: str
    empty_input_behavior: str
    non_finite_input_behavior: str
    tie_behavior: str


class BaseThresholdPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    policy: str
    quantile: float = Field(ge=0.0, le=1.0)
    quantile_estimator: str = "linear_interpolated_order_statistic"


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
    cluster_count: int
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


class SplitConformalThresholdPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

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


class FederatedMatchedExceedancePolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["matched_exceedance"]
    quantile: float = Field(ge=0.0, le=1.0)
    primary_comparator: bool
    client_message: dict[str, JsonValue]
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


class FederatedFixedCoefficientPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["fixed_k"]
    quantile: float = Field(ge=0.0, le=1.0)
    primary_comparator: bool
    supplementary_sensitivity_only: bool
    client_message: dict[str, JsonValue]
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


class MetricBundleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    metrics: list[str]
    cross_client_aggregation: str | None = None
    primary_dispersion_metric: str | None = None
    model_quality_control: str | None = None
    excludes_ineligible_clients: bool | None = None
    requires_attack_evaluable_clients: bool | None = None


class StatisticalProfileConfig(BaseModel):
    """Strict authored statistical-analysis profile (protocols.yaml ``statistical_profiles``).

    A single superset model covering every configured profile shape. ``extra="forbid"``
    rejects unknown or misspelled fields; the model validator enforces the fields that the
    bootstrap methods require. This replaces the previous ``dict[str, JsonValue]`` bag so
    that resolution reads typed attributes instead of untyped mapping lookups.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    estimand: str
    unit_of_analysis: str
    method: str | None = None
    role: str | None = None
    statistic: str | None = None
    confidence_level: float | None = None
    resample_count: int | None = None
    analysis_seed: int | None = None
    analysis_seed_source: str | None = None
    pairing_key: str | None = None
    resampling_unit: str | None = None
    independent_resampling_of_the_two_evaluations: str | None = None
    minimum_paired_units: int | None = None
    minimum_units: int | None = None
    minimum_defined_units: int | None = None
    finite_value_validation: str | None = None
    degenerate_behavior: str | None = None
    direction_source: str | None = None
    bias_correction: str | None = None
    acceleration: str | None = None
    insufficient_pair_behavior: str | None = None
    insufficient_unit_behavior: str | None = None
    missing_pair_behavior: str | None = None
    zero_difference_behavior: str | None = None
    zero_variance_behavior: str | None = None
    diagnostic_intervals_permitted: list[str] | None = None
    multiple_comparison_policy: str | None = None
    per_seed_ratio_reporting: str | None = None
    denominator_materiality_rule: str | None = None
    undefined_denominator_behavior: str | None = None
    interval_reporting: str | None = None
    degradation_gate: str | None = None
    undefined_ratio_behavior: str | None = None
    negative_ratio_behavior: str | None = None
    reported_statistics: list[str] | None = None
    independent_scientific_replication_claim: str | None = None
    procedures: list[str] | None = None
    wilcoxon_alternative: str | None = None
    wilcoxon_zero_difference_handling: str | None = None
    wilcoxon_exact_when_possible: bool | None = None
    wilcoxon_approximation_recorded_when_used: bool | None = None
    effect_size: str | None = None
    unpaired_effect_sizes_forbidden: bool | None = None
    tie_handling: str | None = None
    reported_fields: list[str] | None = None
    interpretation_constraint: str | None = None

    @model_validator(mode="after")
    def validate_bootstrap_requirements(self) -> StatisticalProfileConfig:
        if self.method in {"percentile_bootstrap", "bca_bootstrap"}:
            if self.confidence_level is None:
                raise ValueError("Bootstrap statistical profile requires a confidence_level")
            if self.resample_count is None:
                raise ValueError("Bootstrap statistical profile requires a resample_count")
        return self


class AuthoredProtocolsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int = Field(ge=1)
    model_architectures: dict[str, ModelArchitectureConfig]
    optimizers: dict[str, OptimizerProfileConfig]
    batching: dict[str, BatchingProfileConfig]
    determinism: DeterminismProfileConfig
    seed_cohorts: dict[str, SeedCohortConfig]
    checkpoint_profiles: dict[str, CheckpointProfileConfig]
    training_profiles: dict[str, TrainingProfileConfig]
    eligibility_policies: dict[str, EligibilityPolicyConfig]
    normalization_strategies: dict[str, NormalizationStrategyConfig]
    normalization_fit_scopes: dict[str, str]
    normalization_leakage_rule: str
    quantile_estimators: dict[str, QuantileEstimatorConfig]
    threshold_policy_defaults: dict[str, JsonValue]
    threshold_policies: dict[str, TypedThresholdPolicyConfig]
    metric_definitions: dict[str, JsonValue]
    metric_bundles: dict[str, MetricBundleConfig]
    nested_replicate_policy: dict[str, JsonValue]
    result_types: dict[str, JsonValue]
    evaluation_result_contract: dict[str, JsonValue]
    artifact_identity: dict[str, JsonValue]
    communication_estimation_contract: dict[str, JsonValue]
    report_defaults: dict[str, JsonValue]
    operational_inputs: dict[str, JsonValue]
    statistical_profiles: dict[str, StatisticalProfileConfig]
    report_profiles: dict[str, JsonValue]
    communication_estimation: dict[str, JsonValue] | None = None

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"Unsupported protocols schema version: {value}")
        return value
