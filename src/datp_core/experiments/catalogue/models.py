"""Core experiment catalogue records."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

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
    TrainingProfileId,
)
from datp_core.core.immutability import (
    FrozenJson,
    as_frozen_json_mapping,
    as_optional_frozen_json_mapping,
    as_optional_str_mapping,
    as_str_mapping,
    as_str_mapping_tuple,
)
from datp_core.core.numbers import PositiveInt, Probability
from datp_core.core.seeding import Seed
from datp_core.experiments.catalogue.analyses import AnalysisRecord
from datp_core.experiments.catalogue.evaluations import (
    EvaluationSpecRecord,
    RunRequirement,
)
from datp_core.experiments.catalogue.sweeps import SweepRecord


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


@define(frozen=True, slots=True, kw_only=True)
class CapabilityRequirementRecord:
    capability: str
    when_unavailable: str
    applies_to_populations: tuple[PopulationId, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class PrerequisiteSpecRecord:
    experiment_id: ExperimentId
    required_outcome: str


@define(frozen=True, slots=True, kw_only=True)
class CalibrationSubsetRecord:
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
    identifier: str
    candidate_population: str
    minimum_benign_calibration_count: PositiveInt
    minimum_eligible_client_proportion: Probability
    evaluation_time: str
    failure_outcome: str
    population_reduction_without_explicit_roadmap_authorization: str
    applies_to_experiments: tuple[ExperimentId, ...]


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


@define(frozen=True, slots=True, kw_only=True)
class ResultTypeRecord:
    identifier: str
    permitted_evidence_roles: tuple[str, ...]
