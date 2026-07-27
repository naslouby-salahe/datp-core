"""Core experiment catalogue records."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class CapabilityRequirementRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    capability: str
    when_unavailable: str
    applies_to_populations: tuple[PopulationId, ...] | None


class PrerequisiteSpecRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    experiment_id: ExperimentId
    required_outcome: str


class CalibrationSubsetRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    requested_sample_count: Mapping[str, str]
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
    effective_eligibility_policy_by_sweep_condition: tuple[Mapping[str, str], ...]
    insufficient_row_policy: str
    replicate_aggregation_within_seed: str
    seed_level_statistic: str
    additional_seed_level_statistic: str
    independent_inferential_unit: str
    replicates_counted_as_seeds: bool
    full_calibration_reference_condition: Mapping[str, FrozenJson]

    @field_validator("requested_sample_count", mode="before")
    @classmethod
    def _convert_requested_sample_count(cls, v):
        return as_str_mapping(v)

    @field_validator("effective_eligibility_policy_by_sweep_condition", mode="before")
    @classmethod
    def _convert_effective_eligibility_policy_by_sweep_condition(cls, v):
        return as_str_mapping_tuple(v)

    @field_validator("full_calibration_reference_condition", mode="before")
    @classmethod
    def _convert_full_calibration_reference_condition(cls, v):
        return as_frozen_json_mapping(v)


class EligibilityGateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    identifier: str
    candidate_population: str
    minimum_benign_calibration_count: PositiveInt
    minimum_eligible_client_proportion: Probability
    evaluation_time: str
    failure_outcome: str
    population_reduction_without_explicit_roadmap_authorization: str
    applies_to_experiments: tuple[ExperimentId, ...]


class PopulationRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    identifier: PopulationId
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    metric_bundle_id: MetricBundleId


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
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
    sweeps: tuple[SweepRecord, ...] = Field(default_factory=tuple)
    readiness_gates: tuple[str, ...]
    validation_scope: str | None
    never_promoted_to_confirmatory: bool | None
    outside_core_causal_ladder: bool | None
    faithful_reproduction_claim_forbidden: bool | None
    attack_sensitive_metrics_requested: bool | None
    unavailable_capability_reporting: tuple[Mapping[str, str], ...]
    independent_of_experiment: ExperimentId | None
    calibration_subset: CalibrationSubsetRecord | None
    method_naming_rule: str | None
    personalization_parameter_selection_source: str | None
    run_condition: Mapping[str, str] | None = None
    unavailable_behavior: str | None
    blocks_other_experiments_when_unavailable: bool | None
    estimate_basis: str | None
    client_semantics_constraint: str | None
    generalization_constraint: str | None
    quantitative_claim_gate: str | None
    population_equivalence_requirement: str | None
    population_roles: Mapping[str, str] | None = None
    scope_constraint: str | None
    temporal_procedure: Mapping[str, FrozenJson] | None = None
    primary_coefficient_selection: str | Mapping[str, FrozenJson] | None = None
    training_overrides: Mapping[str, FrozenJson] | None = None

    @field_validator("unavailable_capability_reporting", mode="before")
    @classmethod
    def _convert_unavailable_capability_reporting(cls, v):
        return as_str_mapping_tuple(v)

    @field_validator("run_condition", mode="before")
    @classmethod
    def _convert_run_condition(cls, v):
        return as_optional_str_mapping(v)

    @field_validator("population_roles", mode="before")
    @classmethod
    def _convert_population_roles(cls, v):
        return as_optional_str_mapping(v)

    @field_validator("temporal_procedure", mode="before")
    @classmethod
    def _convert_temporal_procedure(cls, v):
        return as_optional_frozen_json_mapping(v)

    @field_validator("primary_coefficient_selection", mode="before")
    @classmethod
    def _convert_primary_coefficient_selection(cls, v):
        return v if v is None or isinstance(v, str) else as_frozen_json_mapping(v)

    @field_validator("training_overrides", mode="before")
    @classmethod
    def _convert_training_overrides(cls, v):
        return as_optional_frozen_json_mapping(v)


class ResultTypeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    identifier: str
    permitted_evidence_roles: tuple[str, ...]
