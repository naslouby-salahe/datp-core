"""Lightweight typed domain models for configuration dictionaries.

These models replace the former ``Mapping[str, ...]`` fields in
``ResolvedProjectConfiguration``.  They live in a separate module so
that both ``config.models`` and ``config.authored.*`` / ``config.resolution.*``
modules can import them without creating circular dependencies.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import EligibilityPolicyId, NormalizationStrategyId
from datp_core.core.numbers import PositiveInt


class PopulationReadinessRule(BaseModel):
    """Typed population-readiness rule replacing the raw mapping."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    blocked_population_outcome: str
    blocks_only_experiments_binding_that_population: bool
    blocked_population_reporting: str


class AnalysisConventions(BaseModel):
    """Typed analysis conventions replacing the raw mapping."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    paired_delta_definition: str
    delta_direction_resolution: str
    raw_metric_direction_resolution: str


class NormalizationFitScopes(BaseModel):
    """Typed normalization fit scopes replacing the raw mapping."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    global_train: str
    historical_train: str
    per_client_train: str


class EligibilityFallbackRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    threshold_source: str
    shared_construction: str
    reported_status: str
    enters_primary_dispersion: bool


class EligibilityPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: EligibilityPolicyId
    minimum_benign_calibration_count: PositiveInt
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: tuple[str, ...]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: EligibilityFallbackRecord
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None
    permitted_use: str | None


class NormalizationStrategyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: NormalizationStrategyId
    formula: str
    fitted_statistics: tuple[str, ...]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None
