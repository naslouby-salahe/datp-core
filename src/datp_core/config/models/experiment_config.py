"""Pydantic 2 models for authored experiment configuration catalogue (experiments.yaml)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthoredStudyPopulationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    dataset: str
    setup: str
    metric_bundle: str


class CapabilityRequirementConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    capability: str
    when_unavailable: str


class EvaluationSpecConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    label: str
    threshold_policy: str


class AnalysisSpecConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    label: str
    kind: str
    result_type: str
    comparison: str | None = None
    delta_interpretation: str | None = None
    statistical_profile: str | None = None


class AuthoredExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str
    display_name: str
    evidence_role: str
    run_requirement: str
    populations: list[str]
    training_profile: str
    checkpoint_profile: str
    seed_cohort: str
    eligibility_policy: str
    prerequisites: list[Any] = Field(default_factory=list)
    capability_requirements: list[CapabilityRequirementConfig] = Field(default_factory=list)
    evaluations: list[EvaluationSpecConfig] = Field(default_factory=list)
    analyses: list[AnalysisSpecConfig] = Field(default_factory=list)
    report_profiles: list[str] = Field(default_factory=list)
    sweeps: dict[str, Any] | None = None


class AuthoredExperimentsCatalogueConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    schema_version: int = Field(ge=1)
    study_populations: dict[str, AuthoredStudyPopulationConfig]
    capabilities: list[str]
    suppression_behaviors: list[str]
    population_readiness_rule: dict[str, Any]
    eligibility_gates: dict[str, Any]
    analysis_conventions: dict[str, Any]
    experiments: list[AuthoredExperimentConfig]

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"Unsupported experiment schema version: {value}")
        return value
