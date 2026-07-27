"""Authored experiment catalogue document (experiments.yaml)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, JsonValue

from datp_core.config.authored.base import SchemaVersionOneConfigModel, StrictFrozenConfigModel
from datp_core.config.authored.experiments.analyses import AnalysisSpecConfig
from datp_core.config.authored.experiments.evaluations import EvaluationSpecConfig
from datp_core.config.authored.experiments.sweeps import CalibrationSubsetConfig, SweepVariableConfig
from datp_core.config.domain_models import AnalysisConventions, PopulationReadinessRule


class AuthoredStudyPopulationConfig(StrictFrozenConfigModel):
    dataset: str
    setup: str
    metric_bundle: str


class CapabilityRequirementConfig(StrictFrozenConfigModel):
    capability: str
    when_unavailable: str
    applies_to_populations: list[str] | None = None


class PrerequisiteSpecConfig(StrictFrozenConfigModel):
    experiment: str
    required_outcome: str


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
    analyses: list[Annotated[AnalysisSpecConfig, Field(discriminator="kind")]] = Field(default_factory=list)
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
    population_readiness_rule: PopulationReadinessRule
    eligibility_gates: dict[str, EligibilityGateConfig]
    analysis_conventions: AnalysisConventions
    experiments: list[AuthoredExperimentConfig]


__all__ = [
    "AuthoredExperimentConfig",
    "AuthoredExperimentsCatalogueConfig",
    "AuthoredStudyPopulationConfig",
    "CapabilityRequirementConfig",
    "EligibilityGateConfig",
    "PrerequisiteSpecConfig",
]
