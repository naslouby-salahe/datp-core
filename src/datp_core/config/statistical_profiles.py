"""Statistical profile configuration schema."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import StatisticalProfileId
from datp_core.core.numbers import PositiveInt, Probability


class BootstrapMethod(StrEnum):
    BCA_BOOTSTRAP = "bca_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"


class StatisticalMethod(StrEnum):
    """Every `statistical_profiles.*.method` value authored in protocols.yaml.

    A superset of `BootstrapMethod`: comparisons like `profile.method in {BootstrapMethod.X, ...}`
    remain valid because `StrEnum` members compare equal across classes by string value.
    """

    BCA_BOOTSTRAP = "bca_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"
    RATIO_OF_SEED_LEVEL_MEANS = "ratio_of_seed_level_means"
    DESCRIPTIVE_SUMMARY = "descriptive_summary"
    SPEARMAN_CORRELATION = "spearman_correlation"
    LINEAR_REGRESSION = "linear_regression"


class StatisticalProfileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    """Resolved, executable statistical analysis contract (BCa/percentile bootstrap, Wilcoxon, etc.)."""

    identifier: StatisticalProfileId
    method: StatisticalMethod | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


class NestedReplicatePolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


__all__ = [
    "BootstrapMethod",
    "NestedReplicatePolicyRecord",
    "StatisticalMethod",
    "StatisticalProfileRecord",
]
