"""Pure resolved experiment catalogue records: populations, experiments, sweeps, evidence roles,
and the per-experiment analysis-kind specifications (what analysis to run and how -- the typed
*results* of running an analysis are a separate hierarchy owned by analysis/models.py).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, StrEnum
from typing import cast

from attrs import define, field

from datp_core.core.identifiers import (
    CheckpointProfileId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    ExperimentId,
    MetricBundleId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.core.values import (
    FrozenJson,
    PositiveInt,
    Probability,
    RecalibrationMode,
    Seed,
    as_frozen_json_mapping,
    as_optional_frozen_json_mapping,
    as_optional_str_mapping,
    as_str_mapping,
    as_str_mapping_tuple,
    deep_freeze,
)


class EvidenceRole(Enum):
    ANCHOR = "anchor"
    CONFIRMATORY = "confirmatory"
    SENSITIVITY = "sensitivity"
    EXPLORATORY = "exploratory"
    STRESS_TEST = "stress_test"
    COMPARATOR = "comparator"
    MECHANISM = "mechanism"
    SUPPORTIVE = "supportive"
    BOUNDARY = "boundary"
    EXTERNAL_VALIDATION = "external_validation"


class RunRequirement(Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    EXPLORATORY = "exploratory"
    OPTIONAL = "optional"


class SweepConditionAllocation(StrEnum):
    DIRICHLET = "dirichlet"
    EQUAL_ACROSS_SOURCE_DOMAINS = "equal_across_source_domains"


def _as_reference_analysis(value: object) -> str | Mapping[str, str]:
    if isinstance(value, str):
        return value
    return cast("Mapping[str, str]", deep_freeze(value))


@define(frozen=True, slots=True, kw_only=True)
class CapabilityRequirementRecord:
    capability: str
    when_unavailable: str
    applies_to_populations: tuple[PopulationId, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class EvaluationSpecRecord:
    label: str
    threshold_policy_id: ThresholdPolicyId
    run_requirement: RunRequirement
    overrides: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    population_id: PopulationId | None
    recalibration_mode: RecalibrationMode | None


@define(frozen=True, slots=True, kw_only=True)
class PrerequisiteSpecRecord:
    experiment_id: ExperimentId
    required_outcome: str


@define(frozen=True, slots=True, kw_only=True)
class CalibrationSubsetRecord:
    """Pure resolved calibration-subset contract (nested-replicate seed/eligibility semantics)."""

    requested_sample_count: Mapping[str, str] = field(converter=as_str_mapping)
    selection_strategy: str
    nesting_policy: str
    nesting_rule: str
    selection_seed: Seed
    replicate_count: PositiveInt
    replicate_seed_derivation: str
    model_retraining: str
    client_eligibility_per_requested_size: str
    subminimum_eligibility_policy: str
    subminimum_eligibility_policy_applies_to: str
    effective_eligibility_policy_by_sweep_condition: tuple[Mapping[str, str], ...] = field(
        converter=as_str_mapping_tuple
    )
    insufficient_row_policy: str
    replicate_aggregation_within_seed: str
    seed_level_statistic: str
    additional_seed_level_statistic: str
    independent_inferential_unit: str
    replicates_counted_as_seeds: bool
    full_calibration_reference_condition: Mapping[str, FrozenJson] = field(converter=as_frozen_json_mapping)


@define(frozen=True, slots=True, kw_only=True)
class EligibilityGateRecord:
    """Pure resolved catalogue-level eligibility gate (distinct from a per-dataset eligibility policy)."""

    identifier: str
    candidate_population: str
    minimum_benign_calibration_count: PositiveInt
    minimum_eligible_client_proportion: Probability
    evaluation_time: str
    failure_outcome: str
    population_reduction_without_explicit_roadmap_authorization: str
    applies_to_experiments: tuple[ExperimentId, ...]


# --- Analysis specs: one strict variant per authored `kind`, discriminated by kind. Fields are the
# exact authored superset observed for that kind in the six YAML documents (see roadmap 02/03/04);
# genuinely heterogeneous nested contracts (matching_contract, outcome_bands, alternative_path_rule,
# historical_reference) are preserved as frozen JSON rather than speculatively sub-modeled. These
# describe WHAT ANALYSIS TO RUN (catalogue specifications); the typed RESULT of running one lives in
# analysis/models.py's separate result hierarchy.


class AnalysisKind(Enum):
    PAIRED_THRESHOLD = "paired_threshold_analysis"
    ABSORPTION = "absorption_analysis"
    ALERT_BURDEN = "alert_burden_analysis"
    ANCHOR_EQUIVALENCE = "anchor_equivalence_analysis"
    CLUSTER_STABILITY = "cluster_stability_analysis"
    CONFORMAL_COVERAGE = "conformal_coverage_analysis"
    DISTRIBUTION_MECHANISM = "distribution_mechanism_analysis"
    LOCKED_CLIENT_DISTRIBUTION = "locked_client_distribution_analysis"
    METRIC_ASSOCIATION = "metric_association_analysis"
    QUANTILE_ESTIMATION = "quantile_estimation_analysis"
    RECOVERY_FRACTION = "recovery_fraction_analysis"
    RESOURCE_COST = "resource_cost_analysis"
    TEMPORAL_RECOVERY = "temporal_recovery_analysis"
    THRESHOLD_STABILITY = "threshold_stability_analysis"

    @classmethod
    def from_record(cls, record: AnalysisRecord) -> AnalysisKind:
        return cls(record.kind)


@define(frozen=True, slots=True, kw_only=True)
class PairedThresholdAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    secondary_statistical_profile: StatisticalProfileId | None
    first_evaluation: str
    second_evaluation: str
    primary_metric: str
    delta_orientation: str
    delta_interpretation: str
    required_direction: str | None
    monotonicity_required: bool | None
    ordering_inversion_reporting: str | None
    per_sweep_cell: str | None
    full_curve_reporting: str | bool | None
    post_hoc_weight_selection: str | None


@define(frozen=True, slots=True, kw_only=True)
class AbsorptionAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    absorption_metric: str
    formula: str
    band_interpretation: str
    denominator_materiality_rule: float | str
    undefined_denominator_behavior: str
    matching_contract: Mapping[str, FrozenJson] = field(converter=as_frozen_json_mapping)
    outcome_bands: tuple[Mapping[str, str], ...] = field(converter=as_str_mapping_tuple)
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool
    reference_analysis: str | Mapping[str, str] = field(converter=_as_reference_analysis)
    stress_test_analysis: str
    alternative_path_rule: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)


@define(frozen=True, slots=True, kw_only=True)
class AlertBurdenAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    formula: str
    produced_fields: tuple[str, ...]
    source_evaluations: tuple[str, ...]
    required_operational_input: str
    per_client_reporting_required: bool
    unavailable_behavior: str


@define(frozen=True, slots=True, kw_only=True)
class AnchorEquivalenceAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_analysis: str
    comparison_mode: str
    comparison_mode_rule: str
    interval_width_tolerance_multiplier: float
    floating_point_tolerance: Mapping[str, float]
    historical_reference: Mapping[str, float | str]
    statistical_fallback_requirements: tuple[str, ...]
    failure_reasons: tuple[str, ...]
    downstream_blocking_behavior: str


@define(frozen=True, slots=True, kw_only=True)
class ClusterStabilityAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluation: str
    comparison_unit: str
    produced_fields: tuple[str, ...]
    reference_evaluation: str | None
    run_requirement: RunRequirement | None


@define(frozen=True, slots=True, kw_only=True)
class ConformalCoverageAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluation: str
    target_coverage: float
    produced_fields: tuple[str, ...]
    coverage_direction: str | None


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    field_formulas: Mapping[str, str] | None


@define(frozen=True, slots=True, kw_only=True)
class LockedClientDistributionAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    locked_client_identifier: str


@define(frozen=True, slots=True, kw_only=True)
class MetricAssociationAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    secondary_statistical_profile: StatisticalProfileId | None
    predictor_metric: str
    outcome_metric: str
    outcome_source_analysis: str
    interpretation_constraint: str
    grouping_dimension: str | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    oracle_reference: str


@define(frozen=True, slots=True, kw_only=True)
class RecoveryFractionAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    formula: str
    numerator_analysis: str
    denominator_analysis: str
    denominator_composition: str
    denominator_materiality_rule: float | str
    undefined_denominator_behavior: str


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    estimate_basis: str


@define(frozen=True, slots=True, kw_only=True)
class TemporalRecoveryAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    primary_metric: str
    static_reference_evaluation: str
    frozen_evaluation: str
    recalibrated_evaluation: str
    recovery_fields: tuple[str, ...]
    drift_excess_formula: str
    recovered_amount_formula: str
    recovery_ratio_formula: str
    meaningful_degradation_rule: str
    recovery_ratio_precondition: str
    negative_recovery_policy: str
    recovery_ratio_direction: str
    meaningful_recovery_threshold: float
    chronology_unverifiable_policy: str
    outcome_bands: tuple[Mapping[str, str], ...] = field(converter=as_str_mapping_tuple)
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilityAnalysisRecord:
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluation: str
    produced_fields: tuple[str, ...]
    per_sweep_cell: str


AnalysisRecord = (
    PairedThresholdAnalysisRecord
    | AbsorptionAnalysisRecord
    | AlertBurdenAnalysisRecord
    | AnchorEquivalenceAnalysisRecord
    | ClusterStabilityAnalysisRecord
    | ConformalCoverageAnalysisRecord
    | DistributionMechanismAnalysisRecord
    | LockedClientDistributionAnalysisRecord
    | MetricAssociationAnalysisRecord
    | QuantileEstimationAnalysisRecord
    | RecoveryFractionAnalysisRecord
    | ResourceCostAnalysisRecord
    | TemporalRecoveryAnalysisRecord
    | ThresholdStabilityAnalysisRecord
)


SweepValue = str | int | float | tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ValueSweepRecord:
    """A sweep over an explicit authored list of scalar or list-of-string values."""

    name: str
    values: tuple[SweepValue, ...]


@define(frozen=True, slots=True, kw_only=True)
class SweepConditionRecord:
    name: str
    allocation: SweepConditionAllocation
    dirichlet_alpha: float | None


@define(frozen=True, slots=True, kw_only=True)
class ConditionSweepRecord:
    """A sweep over named authored partition/allocation conditions."""

    name: str
    conditions: tuple[SweepConditionRecord, ...]


SweepRecord = ValueSweepRecord | ConditionSweepRecord


@define(frozen=True, slots=True, kw_only=True)
class PopulationRecord:
    identifier: PopulationId
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    metric_bundle_id: MetricBundleId


@define(frozen=True, slots=True, kw_only=True)
class ExperimentRecord:
    identifier: ExperimentId
    display_name: str
    evidence_role: EvidenceRole
    run_requirement: RunRequirement
    population_ids: tuple[PopulationId, ...]
    training_profile_id: TrainingProfileId
    checkpoint_profile_id: CheckpointProfileId
    seed_cohort_id: SeedCohortId
    eligibility_policy_id: EligibilityPolicyId
    prerequisites: tuple[PrerequisiteSpecRecord, ...]
    capability_requirements: tuple[CapabilityRequirementRecord, ...]
    evaluations: tuple[EvaluationSpecRecord, ...]
    analyses: tuple[AnalysisRecord, ...]
    report_ids: tuple[str, ...]
    sweeps: tuple[SweepRecord, ...] = field(factory=tuple)
    readiness_gates: tuple[str, ...]
    validation_scope: str | None
    never_promoted_to_confirmatory: bool | None
    outside_core_causal_ladder: bool | None
    faithful_reproduction_claim_forbidden: bool | None
    attack_sensitive_metrics_requested: bool | None
    unavailable_capability_reporting: tuple[Mapping[str, str], ...] = field(converter=as_str_mapping_tuple)
    independent_of_experiment: ExperimentId | None
    calibration_subset: CalibrationSubsetRecord | None
    method_naming_rule: str | None
    personalization_parameter_selection_source: str | None
    run_condition: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    unavailable_behavior: str | None
    blocks_other_experiments_when_unavailable: bool | None
    estimate_basis: str | None
    client_semantics_constraint: str | None
    generalization_constraint: str | None
    quantitative_claim_gate: str | None
    population_equivalence_requirement: str | None
    population_roles: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    scope_constraint: str | None
    temporal_procedure: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    primary_coefficient_selection: str | Mapping[str, FrozenJson] | None = field(
        converter=lambda v: v if v is None or isinstance(v, str) else as_frozen_json_mapping(v)
    )
    training_overrides: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
