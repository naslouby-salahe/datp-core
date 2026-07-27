"""Lightweight typed domain models for configuration dictionaries.

These models replace the former ``Mapping[str, ...]`` fields in
``ResolvedProjectConfiguration``.  They live in a separate module so
that both ``config.models`` and ``config.authored.*`` / ``config.resolution.*``
modules can import them without creating circular dependencies.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
