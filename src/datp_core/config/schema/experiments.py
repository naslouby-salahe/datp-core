"""Strict Pydantic 2 models for the authored experiment catalogue document (experiments.yaml)."""

from __future__ import annotations

from pydantic import Field, JsonValue, model_validator

from datp_core.config.schema import SchemaVersionOneConfigModel, StrictFrozenConfigModel


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
