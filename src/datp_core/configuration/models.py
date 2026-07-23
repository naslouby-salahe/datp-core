"""Strict Pydantic 2 models for every authored configuration document (datasets, experiments, protocols, runtime).

Every authored configuration model inherits from one of the two base classes defined at the top of
this file, so the strict parsing policy (``extra="forbid"``, ``frozen=True``, ``strict=True``, and the
``schema_version: Literal[1]`` lock) is defined in exactly one place across the whole authored schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from datp_core.pipeline.protocol_types import BootstrapMethod

# --- shared base classes -----------------------------------------------------------------------


class StrictFrozenConfigModel(BaseModel):
    """Base for every authored configuration model.

    ``extra="forbid"`` — unknown YAML keys are rejected.
    ``frozen=True`` — models are immutable after construction.
    ``strict=True`` — Pydantic's strict-mode coercion is enabled (no int→float, etc.).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SchemaVersionOneConfigModel(StrictFrozenConfigModel):
    """Root document model for schema-version-1 authored documents.

    Declares the ``schema_version`` field locked to ``1``.  Any YAML document
    that supplies a different value, or omits the field, is rejected by Pydantic.
    """

    schema_version: Literal[1]


# --- dataset configuration (datasets/<name>.yaml) ----------------------------------------------


class DatasetSourceConfig(StrictFrozenConfigModel):
    role: Literal["executable", "reference_only"]
    root: str
    file_pattern: str
    owns: list[str] | None = None
    permitted_uses: list[str] | None = None
    contributes_rows_to_executable_materializations: bool | None = None
    defines_pseudo_clients: bool | None = None


class CrossSourceRelationshipConfig(StrictFrozenConfigModel):
    row_count_equality_required: bool
    row_level_one_to_one_equivalence_assumed: bool
    join_by_row_position: Literal["forbidden"]
    join_by_any_key: Literal["forbidden"]


class DatasetSourceLayoutConfig(StrictFrozenConfigModel):
    root: str
    benign_file: str | None = None
    benign_file_pattern: str | None = None
    normal_file_pattern: str | None = None
    attack_file_pattern: str | None = None
    device_dirs: list[str] | None = None
    normal_group_folders: list[str] | None = None
    executable_group_folders: list[str] | None = None
    attack_files: list[str] | None = None
    ignored_source_suffixes: list[str] = Field(default_factory=list)
    ignored_root_entries: list[str] = Field(default_factory=list)
    ignored_subtrees: list[str] = Field(default_factory=list)
    sources: dict[str, DatasetSourceConfig] | None = None
    executable_source: str | None = None
    cross_source_relationship: CrossSourceRelationshipConfig | None = None
    normal_traffic_root: str | None = None
    attack_traffic_root: str | None = None
    benign_file_required_per_device: bool | None = None
    attack_family_dirs: list[str] | None = None
    attack_family_required_per_device: bool | None = None


class IdentitySchemeConfig(StrictFrozenConfigModel):
    row_identity: dict[str, str | bool | list[str]]
    client_identity: dict[str, str | bool] | None = None
    benign_group_identity: dict[str, str] | None = None
    attack_row_group_identity: str | None = None
    label_identity: dict[str, str] | None = None
    attack_family_identity: dict[str, str] | None = None
    attack_type_identity: dict[str, str] | None = None
    device_identity: dict[str, str | bool] | None = None
    device_mac_ip_field: str | None = None
    timestamp_field: str | dict[str, str | bool]
    chronological_ordering_basis: str | None = None
    provenance_fields: list[str]


class EndpointIdentityConfig(StrictFrozenConfigModel):
    resolution: str
    fields: list[str]
    internal_prefix: str
    subnet_component: str
    subnet_role_source: str
    subnet_to_group: dict[int, str]
    excluded_endpoints: dict[str, list[str] | str]
    direction_normalization: str
    use: str
    unresolved_row_policy: str


class RetainedNumericFeaturesConfig(StrictFrozenConfigModel):
    role: Literal["model_feature"]
    order: list[str]
    numeric_parsing: dict[str, list[str] | str]
    on_invalid_value: str


class CategoricalEncodingConfig(StrictFrozenConfigModel):
    strategy: str
    columns: list[str]
    vocabulary_scope: str
    vocabulary_artifact: str
    vocabulary_fingerprint: str
    category_order: str
    encoded_feature_naming: str
    missing_category_policy: str
    unknown_category_policy: str
    unknown_indicator_distinct_from_missing_indicator: bool
    feature_order: list[str]


class ModelFeaturesConfig(StrictFrozenConfigModel):
    role: Literal["model_feature"]
    type: str
    order: list[str]


class MulticlassLabelConfig(StrictFrozenConfigModel):
    column: str
    type: str | None = None
    case: str | None = None


class LabelFieldsConfig(StrictFrozenConfigModel):
    binary_label: dict[str, str | list[int] | list[str]]
    multiclass_label: MulticlassLabelConfig | None = None
    benign_value: dict[str, str | int] | None = None
    attack_class_mapping: dict[str, str] | None = None
    device_family_mapping: dict[str, str] | None = None
    family_taxonomy: str | None = None
    family_map: dict[str, str] | None = None


class DatasetFieldSchemaConfig(StrictFrozenConfigModel):
    source_column_count: int | dict[str, int]
    header_required: bool
    header_must_be_identical_across_all_source_files: bool | None = None
    header_must_be_identical_across_all_files_in_a_tree: bool | None = None
    merged_header_extends_per_class_header_with: str | None = None
    label_column_position: str | None = None
    identity_scheme: IdentitySchemeConfig
    label_fields: LabelFieldsConfig
    model_features: ModelFeaturesConfig | None = None
    source_columns: list[str] | None = None
    endpoint_identity: EndpointIdentityConfig | None = None
    attack_row_group_policy: dict[str, str] | None = None
    retained_numeric_features: RetainedNumericFeaturesConfig | None = None
    post_encoding_feature_order: str | None = None
    categorical_encoding: str | CategoricalEncodingConfig
    leakage_exclusions: list[str] | dict[str, str | list[str]]


class NormalizationSpecConfig(StrictFrozenConfigModel):
    strategy: str
    scope: str


class SplitSpecConfig(StrictFrozenConfigModel):
    method: str
    calibration_benign_only: bool
    split_seed: int | None = None
    ratios: dict[str, float] | None = None
    ordering_basis: str | None = None
    ordering_scope: str | None = None
    gap_handling: str | None = None
    attack_rows: str | None = None
    attack_test_membership: str | None = None
    attack_ordering: str | None = None
    benign_attack_deduplication: str | None = None
    role_order: list[str] | None = None
    excluded_client_folders: list[str] | None = None
    exclusion_reason: str | None = None
    historical_train_fraction: float | None = None
    historical_calibration_fraction: float | None = None
    future_recalibration_fraction: float | None = None
    future_evaluation_fraction: float | None = None
    ordering_field: str | None = None
    ordering_sort: str | None = None
    rollover_policy: str | None = None
    rollover_scope: str | None = None
    boundary_rule: str | None = None
    boundary_index_formula: str | None = None
    future_leakage_check: str | None = None
    minimum_row_counts: dict[str, int] | None = None
    missing_client_policy: str | None = None
    chronology_unverifiable_policy: str | None = None


class MaterializationConfig(StrictFrozenConfigModel):
    materialization_id: str
    role: str | None = None
    normalization: NormalizationSpecConfig
    vocabulary_fit_split: str | None = None
    preprocessing_sequence: list[str]
    row_exclusion: dict[str, str | bool]
    split: SplitSpecConfig
    split_row_semantics: dict[str, str | bool] | None = None
    infeasibility_policy: str | None = None


class SetupClientConstructionConfig(StrictFrozenConfigModel):
    method: str
    client_source: str | list[str] | None = None
    client_semantics: str | None = None
    excluded_client_folders: list[str] | None = None
    client_count: int | None = None
    partition_condition: dict[str, str] | None = None
    source_mixture_components: str | None = None
    label_field: str | None = None
    partition_seed: int | None = None
    partition_axes: dict[str, str] | None = None
    allocation_procedure: dict[str, str] | None = None
    same_proportions_govern: list[str] | None = None
    split_role_preservation: str | None = None
    attack_row_assignment: str | None = None
    attack_labels_used_in_partition_generation: bool | None = None
    minimum_row_counts: dict[str, int] | None = None
    retry_policy: dict[str, str | int] | None = None
    feasibility_failure: str | None = None
    manifest_invariants: list[str] | None = None
    manifest_fields: list[str] | None = None


class SetupConfig(StrictFrozenConfigModel):
    materialization: str
    client_construction: SetupClientConstructionConfig
    provides_capabilities: list[str]
    validation_scope: str | None = None
    eligibility_gate: str | None = None
    client_population_must_equal_setup: str | None = None


class SourceContractConfig(StrictFrozenConfigModel):
    every_model_feature_present_in_merged_header: bool | None = None
    every_model_feature_present_in_every_file: bool | None = None
    model_feature_count_equals_source_column_count: bool | None = None
    per_class_schema_reference_check: dict[str, str | bool] | None = None
    malformed_row: dict[str, str] | None = None
    empty_label_row: dict[str, str] | None = None
    reject_unparseable_numeric_model_feature: bool | None = None
    reject_row_with_field_count_other_than_header: bool | None = None
    column_role_partition: dict[str, list[str] | bool] | None = None
    positional_contract: dict[str, bool] | None = None
    row_integrity_exclusions: dict[str, list[str] | bool | dict[str, dict[str, str]]] | None = None


class FingerprintInputsConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, populate_by_name=True)

    source: list[str]
    schema_fields: list[str] = Field(alias="schema")
    materialization: list[str]
    client_assignment: list[str]


class AuthoredDatasetConfig(SchemaVersionOneConfigModel):
    dataset: str
    display_name: str
    schema_id: str
    source_layout: DatasetSourceLayoutConfig
    field_schema: DatasetFieldSchemaConfig
    source_contract: SourceContractConfig
    fingerprint_inputs: FingerprintInputsConfig
    client_identity_contract: dict[str, str | list[str]] | None = None
    eligibility_policy: str
    materializations: dict[str, MaterializationConfig]
    setups: dict[str, SetupConfig]


# --- experiment catalogue configuration (experiments.yaml) -------------------------------------


class AuthoredStudyPopulationConfig(StrictFrozenConfigModel):
    dataset: str
    setup: str
    metric_bundle: str


class CapabilityRequirementConfig(StrictFrozenConfigModel):
    capability: str
    when_unavailable: str
    applies_to_populations: list[str] | None = None


class EvaluationSpecConfig(StrictFrozenConfigModel):
    label: str
    threshold_policy: str
    overrides: dict[str, JsonValue] | None = None
    run_requirement: str | None = None
    population: str | None = None
    recalibration_mode: str | None = None


class AnalysisSpecConfig(StrictFrozenConfigModel):
    label: str
    kind: str
    result_type: str

    first_evaluation: str | None = None
    second_evaluation: str | None = None
    source_evaluations: list[str] | None = None
    source_evaluation: str | None = None
    reference_evaluation: str | None = None
    source_analysis: str | None = None
    numerator_analysis: str | None = None
    denominator_analysis: str | None = None
    denominator_composition: str | None = None
    primary_metric: str | None = None
    predictor_metric: str | None = None
    outcome_metric: str | None = None
    outcome_source_analysis: str | None = None
    grouping_dimension: str | None = None
    delta_orientation: str | None = None
    delta_interpretation: str | None = None
    required_direction: str | None = None
    comparison_mode: str | None = None
    comparison_mode_rule: str | None = None
    comparison_unit: str | None = None
    produced_fields: list[str] | None = None
    field_formulas: dict[str, str] | None = None
    locked_client_identifier: str | None = None
    per_sweep_cell: str | None = None
    ordering_inversion_reporting: str | None = None
    monotonicity_required: bool | None = None
    interpretation_constraint: str | None = None
    formula: str | None = None
    undefined_denominator_behavior: str | None = None
    denominator_materiality_rule: float | str | None = None
    target_coverage: float | None = None
    coverage_direction: str | None = None
    oracle_reference: str | None = None
    statistical_fallback_requirements: list[str] | None = None
    historical_reference: dict[str, float | str] | None = None
    interval_width_tolerance_multiplier: float | None = None
    floating_point_tolerance: dict[str, float] | None = None
    failure_reasons: list[str] | None = None
    downstream_blocking_behavior: str | None = None
    full_curve_reporting: str | bool | None = None
    post_hoc_weight_selection: str | None = None

    statistical_profile: str | None = None
    secondary_statistical_profile: str | None = None
    run_requirement: str | None = None
    reference_analysis: str | dict[str, str] | None = None
    stress_test_analysis: str | None = None
    absorption_metric: str | None = None
    matching_contract: dict[str, JsonValue] | None = None
    outcome_bands: list[dict[str, str]] | None = None
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool | None = None
    alternative_path_rule: dict[str, JsonValue] | None = None
    band_interpretation: str | None = None
    required_operational_input: str | None = None
    per_client_reporting_required: bool | None = None
    unavailable_behavior: str | None = None
    estimate_basis: str | None = None
    static_reference_evaluation: str | None = None
    frozen_evaluation: str | None = None
    recalibrated_evaluation: str | None = None
    recovery_fields: list[str] | None = None
    drift_excess_formula: str | None = None
    recovered_amount_formula: str | None = None
    recovery_ratio_formula: str | None = None
    meaningful_degradation_rule: str | None = None
    recovery_ratio_precondition: str | None = None
    negative_recovery_policy: str | None = None
    recovery_ratio_direction: str | None = None
    meaningful_recovery_threshold: float | None = None
    chronology_unverifiable_policy: str | None = None


class PrerequisiteSpecConfig(StrictFrozenConfigModel):
    experiment: str
    required_outcome: str


class SweepConditionConfig(StrictFrozenConfigModel):
    name: str
    allocation: str
    dirichlet_alpha: float | None = None


class SweepVariableConfig(StrictFrozenConfigModel):
    values: list[JsonValue] | None = None
    conditions: list[SweepConditionConfig] | None = None

    @model_validator(mode="after")
    def validate_exactly_one_variant(self) -> SweepVariableConfig:
        if (self.values is None) == (self.conditions is None):
            raise ValueError("A sweep variable must author exactly one of 'values' or 'conditions'")
        return self


class CalibrationSubsetConfig(StrictFrozenConfigModel):
    requested_sample_count: dict[str, str]
    selection_strategy: str
    nesting_policy: str
    nesting_rule: str
    selection_seed: int
    replicate_count: int
    replicate_seed_derivation: str
    model_retraining: str
    client_eligibility_per_requested_size: str
    subminimum_eligibility_policy: str
    subminimum_eligibility_policy_applies_to: str
    effective_eligibility_policy_by_sweep_condition: list[dict[str, str]]
    insufficient_row_policy: str
    replicate_aggregation_within_seed: str
    seed_level_statistic: str
    additional_seed_level_statistic: str
    independent_inferential_unit: str
    replicates_counted_as_seeds: bool
    full_calibration_reference_condition: dict[str, JsonValue]


class AuthoredExperimentConfig(StrictFrozenConfigModel):
    name: str
    display_name: str
    evidence_role: str
    run_requirement: str
    populations: list[str]
    training_profile: str
    checkpoint_profile: str
    seed_cohort: str
    eligibility_policy: str
    readiness_gates: list[str] = Field(default_factory=list)
    prerequisites: list[PrerequisiteSpecConfig] = Field(default_factory=list)
    capability_requirements: list[CapabilityRequirementConfig] = Field(default_factory=list)
    validation_scope: str | None = None
    never_promoted_to_confirmatory: bool | None = None
    outside_core_causal_ladder: bool | None = None
    faithful_reproduction_claim_forbidden: bool | None = None
    attack_sensitive_metrics_requested: bool | None = None
    unavailable_capability_reporting: list[dict[str, str]] = Field(default_factory=list)
    independent_of_experiment: str | None = None
    sweeps: dict[str, SweepVariableConfig] | None = None
    calibration_subset: CalibrationSubsetConfig | None = None
    evaluations: list[EvaluationSpecConfig] = Field(default_factory=list)
    analyses: list[AnalysisSpecConfig] = Field(default_factory=list)
    reports: list[str] = Field(default_factory=list)
    method_naming_rule: str | None = None
    personalization_parameter_selection_source: str | None = None
    run_condition: dict[str, str] | None = None
    unavailable_behavior: str | None = None
    blocks_other_experiments_when_unavailable: bool | None = None
    estimate_basis: str | None = None
    client_semantics_constraint: str | None = None
    generalization_constraint: str | None = None
    quantitative_claim_gate: str | None = None
    population_equivalence_requirement: str | None = None
    population_roles: dict[str, str] | None = None
    scope_constraint: str | None = None
    temporal_procedure: dict[str, JsonValue] | None = None
    primary_coefficient_selection: str | dict[str, JsonValue] | None = None
    training_overrides: dict[str, JsonValue] | None = None


class EligibilityGateConfig(StrictFrozenConfigModel):
    candidate_population: str
    minimum_benign_calibration_count: int
    minimum_eligible_client_proportion: float
    evaluation_time: str
    failure_outcome: str
    population_reduction_without_explicit_roadmap_authorization: str
    applies_to_experiments: list[str]


class AuthoredExperimentsCatalogueConfig(SchemaVersionOneConfigModel):
    study_populations: dict[str, AuthoredStudyPopulationConfig]
    capabilities: list[str]
    suppression_behaviors: list[str]
    population_readiness_rule: dict[str, str | bool]
    eligibility_gates: dict[str, EligibilityGateConfig]
    analysis_conventions: dict[str, str]
    experiments: list[AuthoredExperimentConfig]


# --- protocol configuration (protocols.yaml) ----------------------------------------------------


class ModelInputDimensionConfig(StrictFrozenConfigModel):
    resolution: str
    declared_per_dataset: bool
    validation: str


class ModelDecoderConfig(StrictFrozenConfigModel):
    construction: str
    final_layer_output_dim: str


class ModelParameterInitializationConfig(StrictFrozenConfigModel):
    weight: str
    bias: str
    applied_to: str
    seeded_by: str


class ModelAnomalyScoreConfig(StrictFrozenConfigModel):
    definition: str
    orientation: str


class ModelArchitectureConfig(StrictFrozenConfigModel):
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


class OptimizerProfileConfig(StrictFrozenConfigModel):
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


class BatchingProfileConfig(StrictFrozenConfigModel):
    micro_batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    shuffle_each_epoch: bool
    shuffle_unit: str
    incomplete_final_batch: str
    row_ordering_before_shuffle: str
    shuffle_seed_namespace: str
    worker_seed_namespace: str


class SeedNamespaceConfig(StrictFrozenConfigModel):
    key: str
    components: list[str]


class DeterminismProfileConfig(StrictFrozenConfigModel):
    seed_domains: list[str]
    partition_seed_independent_of_training_seeds: bool
    checkpoint_selection_uses_no_stochastic_seed: bool
    derived_seed_algorithm: dict[str, str | int]
    seed_namespaces: dict[str, SeedNamespaceConfig]
    resolved_seeds_required_in_manifests: list[str]


class SeedCohortConfig(StrictFrozenConfigModel):
    paired_seed_count: int
    training_seeds: list[int]
    bootstrap_analysis_seed: int
    analysis_seed_model: str

    @model_validator(mode="after")
    def validate_seed_cohort(self) -> SeedCohortConfig:
        if len(self.training_seeds) != self.paired_seed_count:
            raise ValueError("paired_seed_count must equal the number of training_seeds")
        if len(set(self.training_seeds)) != len(self.training_seeds):
            raise ValueError("training_seeds must be unique")
        return self


class CheckpointSelectorInputConfig(StrictFrozenConfigModel):
    population: str
    quantity: str
    client_weighting: str | None = None
    aggregation_over_clients: str | None = None
    client_accumulation_order: str | None = None
    aggregation_over_rows: str | None = None


class CheckpointSelectionConfig(StrictFrozenConfigModel):
    rule: str
    selector_input: CheckpointSelectorInputConfig | None = None
    tie_break: str | None = None
    aggregation: str | None = None
    scope: str | None = None
    selected_round_reuse: str | None = None
    weights_remain_seed_and_population_specific: bool | None = None
    forbidden_selectors: list[str] | None = None
    selection_granularity: str | None = None


class CheckpointConvergenceConfig(StrictFrozenConfigModel):
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


class CheckpointProfileConfig(StrictFrozenConfigModel):
    total_rounds: int | None = None
    total_epochs: int | None = None
    rounds: list[int] | None = None
    epochs: list[int] | None = None
    early_stopping: str
    convergence: CheckpointConvergenceConfig | None = None
    convergence_logged_without_stopping: bool | None = None
    checkpoint_save_policy: str | None = None
    selection: CheckpointSelectionConfig


class FederationStrategyConfig(StrictFrozenConfigModel):
    """Authored Flower FedAvg participation contract."""

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: int
    minimum_evaluate_clients: int
    minimum_available_clients: int


class TrainingProfileConfig(StrictFrozenConfigModel):
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


class EligibilityFallbackConfig(StrictFrozenConfigModel):
    threshold_source: str
    shared_construction: str
    reported_status: str
    enters_primary_dispersion: bool


class EligibilityPolicyConfig(StrictFrozenConfigModel):
    minimum_benign_calibration_count: int
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: list[str]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: EligibilityFallbackConfig
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None = None
    permitted_use: str | None = None


class NormalizationStrategyConfig(StrictFrozenConfigModel):
    formula: str
    fitted_statistics: list[str]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None = None


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


class FederatedFixedCoefficientPolicyConfig(StrictFrozenConfigModel):
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


class MetricBundleConfig(StrictFrozenConfigModel):
    metrics: list[str]
    cross_client_aggregation: str | None = None
    primary_dispersion_metric: str | None = None
    model_quality_control: str | None = None
    excludes_ineligible_clients: bool | None = None
    requires_attack_evaluable_clients: bool | None = None


class StatisticalProfileConfig(StrictFrozenConfigModel):
    """Strict authored statistical-analysis profile (protocols.yaml ``statistical_profiles``).

    A single superset model covering every configured profile shape. ``extra="forbid"``
    rejects unknown or misspelled fields; the model validator enforces the fields that the
    bootstrap methods require. This replaces a ``dict[str, JsonValue]`` bag so that resolution
    reads typed attributes instead of untyped mapping lookups.
    """

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
        if self.method in {BootstrapMethod.PERCENTILE_BOOTSTRAP, BootstrapMethod.BCA_BOOTSTRAP}:
            if self.confidence_level is None:
                raise ValueError("Bootstrap statistical profile requires a confidence_level")
            if self.resample_count is None:
                raise ValueError("Bootstrap statistical profile requires a resample_count")
        return self


class ThresholdPolicyDefaultsConfig(StrictFrozenConfigModel):
    source_score_population: str
    eligibility_filter: str
    attack_rows_forbidden_in_calibration: bool
    non_finite_calibration_score: str
    empty_client_calibration: str
    application_scope: str
    required_diagnostic_fields: list[str]


class NestedReplicatePolicyConfig(StrictFrozenConfigModel):
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


class ResultTypeConfig(StrictFrozenConfigModel):
    permitted_evidence_roles: list[str]


class EvaluationResultContractConfig(StrictFrozenConfigModel):
    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: list[str]


class ReportDefaultsConfig(StrictFrozenConfigModel):
    ordering: str
    missing_value_policy: str
    table_output_formats: list[str]
    figure_output_formats: list[str]
    provenance_required_per_artifact: bool
    analysis_defined_direction_token: str


class ReportColumnConfig(StrictFrozenConfigModel):
    name: str
    unit: str
    direction: str


class ReportProfileConfig(StrictFrozenConfigModel):
    artifact_type: str
    table_type: str | None = None
    figure_type: str | None = None
    estimate_basis: str | None = None
    columns: list[ReportColumnConfig] | None = None
    series: list[ReportColumnConfig] | None = None


class BenignDecisionRateConfig(StrictFrozenConfigModel):
    configured: bool
    value: float | None = None
    required_fields: list[str]
    finite_value_validation: str
    non_negative_validation: str
    unavailable_behavior: str
    invented_rate_forbidden: bool


class OperationalInputsConfig(StrictFrozenConfigModel):
    benign_decision_rate: BenignDecisionRateConfig


class ArtifactFingerprintsConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, populate_by_name=True)

    source: list[str]
    schema_stage: list[str] = Field(alias="schema")
    materialization: list[str]
    client_assignment: list[str]
    model_stage: list[str] = Field(alias="model")
    training: list[str]
    checkpoint: list[str]
    score: list[str]
    threshold: list[str]
    metric: list[str]
    analysis: list[str]


class ArtifactIdentityConfig(StrictFrozenConfigModel):
    hash_function: str
    digest_bytes: int
    canonical_serialization: str
    absolute_paths_excluded_from_identity: bool
    fingerprints: ArtifactFingerprintsConfig
    lineage_validation_before_reuse: list[str]
    reuse_rejected_when_any_changes: list[str]


class FieldEncodingConfig(StrictFrozenConfigModel):
    bytes_per_field: int
    byte_order: str


class ThresholdExchangeEntryConfig(StrictFrozenConfigModel):
    uplink_fields_per_client: list[str] | None = None
    downlink_fields_per_client: list[str] | None = None
    candidate_grid_downlink_fields_per_client: list[str] | None = None
    candidate_grid_uplink_fields_per_client_per_candidate: list[str] | None = None


class ThresholdExchangeConfig(StrictFrozenConfigModel):
    direction: str
    b1: ThresholdExchangeEntryConfig
    b2: ThresholdExchangeEntryConfig
    b4: ThresholdExchangeEntryConfig
    federated_summary: ThresholdExchangeEntryConfig


class ModelExchangeConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, protected_namespaces=())

    field_width: str
    directions: list[str]
    bytes_per_round_formula: str


class CheckpointStorageConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, protected_namespaces=())

    contents: list[str]
    model_parameter_bytes_formula: str


class CommunicationEstimationContractConfig(StrictFrozenConfigModel):
    estimate_basis: str
    field_encodings: dict[str, FieldEncodingConfig]
    threshold_exchange: ThresholdExchangeConfig
    candidate_grid_payload: str
    model_exchange: ModelExchangeConfig
    checkpoint_storage: CheckpointStorageConfig
    filename_match_is_not_lineage_evidence: bool
    frozen_artifacts_immutable: bool
    ambiguous_latest_reference: str


class MetricFormulaConfig(StrictFrozenConfigModel):
    """Reusable strict leaf descriptor for a single metric definition (superset of all metric keys)."""

    formula: str | None = None
    unit: str | None = None
    direction: str | None = None
    zero_denominator: str | None = None
    requires: list[str] | None = None
    missing_class_behavior: str | None = None
    requires_both_classes: bool | None = None
    role: str | None = None
    invariance_check: str | None = None
    quantile_estimator: str | None = None
    zero_sum_behavior: str | None = None
    zero_oracle_behavior: str | None = None
    zero_mean_behavior: str | None = None
    denominator_stabilizer: str | None = None
    near_zero_mean_threshold_formula: str | None = None
    near_zero_mean_behavior: str | None = None
    near_zero_mean_threshold_factor: float | None = None
    minimum_client_count: int | None = None
    weighting: str | None = None
    comparison_unit: str | None = None


class CrossClientAggregationConfig(StrictFrozenConfigModel):
    mean_fpr: MetricFormulaConfig
    standard_deviation_ddof: int
    cv_fpr: MetricFormulaConfig
    cv_tpr: MetricFormulaConfig
    iqr_fpr: MetricFormulaConfig
    fpr_range: MetricFormulaConfig
    worst_client_fpr: MetricFormulaConfig
    p10_macro_f1: MetricFormulaConfig
    worst_client_ba: MetricFormulaConfig
    jain_index: MetricFormulaConfig
    gini_coefficient: MetricFormulaConfig


class ThresholdEstimationMetricsConfig(StrictFrozenConfigModel):
    absolute_threshold_error: MetricFormulaConfig
    relative_threshold_error: MetricFormulaConfig
    oracle_definition: str
    target_exceedance: MetricFormulaConfig
    signed_attainment_error: MetricFormulaConfig
    absolute_attainment_error: MetricFormulaConfig
    threshold_dispersion: MetricFormulaConfig
    threshold_variance_across_replicates: MetricFormulaConfig


class JsDivergenceConfig(StrictFrozenConfigModel):
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


class HeterogeneityDiagnosticsConfig(StrictFrozenConfigModel):
    pairwise_js_divergence: JsDivergenceConfig


class ClusterDiagnosticsConfig(StrictFrozenConfigModel):
    adjusted_rand_index: MetricFormulaConfig
    within_cluster_dispersion: MetricFormulaConfig
    across_cluster_dispersion: MetricFormulaConfig


class PrecisionPolicyConfig(StrictFrozenConfigModel):
    computation: str
    rounding: str


class MetricDefinitionsConfig(StrictFrozenConfigModel):
    prediction_rule: str
    per_client_before_aggregation: bool
    test_rows_only: bool
    fpr: MetricFormulaConfig
    tpr: MetricFormulaConfig
    balanced_accuracy: MetricFormulaConfig
    macro_f1: MetricFormulaConfig
    auroc: MetricFormulaConfig
    cross_client_aggregation: CrossClientAggregationConfig
    threshold_estimation: ThresholdEstimationMetricsConfig
    heterogeneity_diagnostics: HeterogeneityDiagnosticsConfig
    cluster_diagnostics: ClusterDiagnosticsConfig
    precision_policy: PrecisionPolicyConfig
    metric_statuses: list[str]
    forbidden_substitutions: list[str]


class AuthoredProtocolsConfig(SchemaVersionOneConfigModel):
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
    threshold_policy_defaults: ThresholdPolicyDefaultsConfig
    threshold_policies: dict[str, TypedThresholdPolicyConfig]
    metric_definitions: MetricDefinitionsConfig
    metric_bundles: dict[str, MetricBundleConfig]
    nested_replicate_policy: NestedReplicatePolicyConfig
    result_types: dict[str, ResultTypeConfig]
    evaluation_result_contract: EvaluationResultContractConfig
    artifact_identity: ArtifactIdentityConfig
    communication_estimation_contract: CommunicationEstimationContractConfig
    report_defaults: ReportDefaultsConfig
    operational_inputs: OperationalInputsConfig
    statistical_profiles: dict[str, StatisticalProfileConfig]
    report_profiles: dict[str, ReportProfileConfig]
    communication_estimation: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def reject_retired_policy_identifiers(self) -> AuthoredProtocolsConfig:
        retired = {"b5", "b3lgs"}
        for identifier in self.threshold_policies:
            normalized = identifier.lower().replace("-", "").replace("_", "")
            if normalized in retired:
                raise ValueError(f"Retired threshold policy identifier is forbidden: {identifier}")
        return self


# --- runtime configuration (runtime.yaml) -------------------------------------------------------


class DataLoadingConfig(StrictFrozenConfigModel):
    """Strict typed contract for per-execution-profile data-loading settings."""

    chunk_row_count: int
    streaming: bool


class ResourceBudgetConfig(StrictFrozenConfigModel):
    """Strict typed contract for per-execution-profile resource budget."""

    max_ram_gib: int
    max_vram_gib: int | None = None


class ConcurrencyConfig(StrictFrozenConfigModel):
    """Strict typed contract for per-execution-profile concurrency limits.

    Fields vary across execution profiles; all are optional except ``worker_count``.
    """

    worker_count: int
    training_concurrency: int | None = None
    scoring_concurrency: int | None = None
    audit_concurrency: int | None = None


class RawSourcePolicyConfig(StrictFrozenConfigModel):
    follow_symlink: bool
    require_resolved_target_readable: bool
    reject_broken_symlink: bool
    reject_symlink_loop: bool
    write_access: str
    create_files_under_raw_root: str


class DeterminismStrictConfig(StrictFrozenConfigModel):
    python_hash_seed: int
    cublas_workspace_config: str
    torch_use_deterministic_algorithms: bool
    torch_deterministic_algorithms_warn_only: bool
    cudnn_deterministic: bool
    cudnn_benchmark: bool
    float32_matmul_precision: str
    tensorfloat32_matmul: bool
    tensorfloat32_cudnn: bool
    dataloader_worker_seeding: str
    file_discovery_order: str
    client_iteration_order: str
    nondeterministic_operation_policy: str
    recorded_environment_fields: list[str]
    unavailable_determinism_policy: str


class DeterminismEnforcementConfig(StrictFrozenConfigModel):
    strict: DeterminismStrictConfig


class DevicePolicyRulesConfig(StrictFrozenConfigModel):
    cuda_required: dict[str, str]
    cpu_only: dict[str, list[str] | bool]


class ResourcePressurePolicyConfig(StrictFrozenConfigModel):
    silent_reduction_of_batch_size: str
    silent_reduction_of_rounds_seeds_clients_or_sample_counts: str
    on_budget_exceeded: str


class ExecutionProfileConfig(StrictFrozenConfigModel):
    device_policy: str
    determinism: str
    resource_budget: ResourceBudgetConfig
    concurrency: ConcurrencyConfig
    data_loading: DataLoadingConfig
    process_start_method: str
    log_interval_rounds: int
    atomic_write: bool
    temporary_storage: str | None = None
    temporary_storage_cleanup: str | None = None


class AuthoredRuntimeConfig(SchemaVersionOneConfigModel):
    roots: dict[str, str]
    raw_source_policy: RawSourcePolicyConfig
    determinism_enforcement: DeterminismEnforcementConfig
    device_policy_rules: DevicePolicyRulesConfig
    resource_pressure_policy: ResourcePressurePolicyConfig
    execution_profiles: dict[str, ExecutionProfileConfig]
