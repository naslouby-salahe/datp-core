"""Authored sweep-variable and calibration-subset contracts (experiments.yaml)."""

from __future__ import annotations

from pydantic import JsonValue, model_validator

from datp_core.config.authored.base import StrictFrozenConfigModel


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
