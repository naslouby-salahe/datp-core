"""Authored statistical-analysis profile contract (protocols.yaml ``statistical_profiles``)."""

from __future__ import annotations

from pydantic import model_validator

from datp_core.config.authored.base import StrictFrozenConfigModel
from datp_core.config.statistical_profiles import BootstrapMethod


class StatisticalProfileConfig(StrictFrozenConfigModel):
    """Strict authored statistical-analysis profile (protocols.yaml ``statistical_profiles``).

    A single superset model covering every configured profile shape. ``extra="forbid"``
    rejects unknown or misspelled fields; the model validator enforces the fields that the
    bootstrap methods require. This replaces a ``dict[str, JsonValue]`` bag so that resolution
    reads typed attributes instead of untyped mapping lookups.
    """

    estimand: str
    unit_of_analysis: str
    method: str | None = None
    role: str | None = None
    statistic: str | None = None
    confidence_level: float | None = None
    resample_count: int | None = None
    analysis_seed: int | None = None
    analysis_seed_source: str | None = None
    pairing_key: str | None = None
    resampling_unit: str | None = None
    independent_resampling_of_the_two_evaluations: str | None = None
    minimum_paired_units: int | None = None
    minimum_units: int | None = None
    minimum_defined_units: int | None = None
    finite_value_validation: str | None = None
    degenerate_behavior: str | None = None
    direction_source: str | None = None
    bias_correction: str | None = None
    acceleration: str | None = None
    insufficient_pair_behavior: str | None = None
    insufficient_unit_behavior: str | None = None
    missing_pair_behavior: str | None = None
    zero_difference_behavior: str | None = None
    zero_variance_behavior: str | None = None
    diagnostic_intervals_permitted: list[str] | None = None
    multiple_comparison_policy: str | None = None
    per_seed_ratio_reporting: str | None = None
    denominator_materiality_rule: str | None = None
    undefined_denominator_behavior: str | None = None
    interval_reporting: str | None = None
    degradation_gate: str | None = None
    undefined_ratio_behavior: str | None = None
    negative_ratio_behavior: str | None = None
    reported_statistics: list[str] | None = None
    independent_scientific_replication_claim: str | None = None
    procedures: list[str] | None = None
    wilcoxon_alternative: str | None = None
    wilcoxon_zero_difference_handling: str | None = None
    wilcoxon_exact_when_possible: bool | None = None
    wilcoxon_approximation_recorded_when_used: bool | None = None
    effect_size: str | None = None
    unpaired_effect_sizes_forbidden: bool | None = None
    tie_handling: str | None = None
    reported_fields: list[str] | None = None
    interpretation_constraint: str | None = None

    @model_validator(mode="after")
    def validate_bootstrap_requirements(self) -> StatisticalProfileConfig:
        if self.method in {BootstrapMethod.PERCENTILE_BOOTSTRAP, BootstrapMethod.BCA_BOOTSTRAP}:
            if self.confidence_level is None:
                raise ValueError("Bootstrap statistical profile requires a confidence_level")
            if self.resample_count is None:
                raise ValueError("Bootstrap statistical profile requires a resample_count")
        return self
