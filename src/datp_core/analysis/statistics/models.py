"""Shared statistical value types used across every analysis capability."""

from __future__ import annotations

from enum import StrEnum

from attrs import define

from datp_core.core.identifiers import MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.core.numbers import PositiveInt, Probability
from datp_core.core.seeding import Seed


class StatisticalProcedureError(ValueError):
    """A locked statistical procedure cannot produce a scientifically valid result."""


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


@define(frozen=True, slots=True, kw_only=True)
class StatisticalProfileRecord:
    """Resolved, executable statistical analysis contract (BCa/percentile bootstrap, Wilcoxon, etc.)."""

    identifier: StatisticalProfileId
    method: StatisticalMethod | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


@define(frozen=True, slots=True, kw_only=True)
class NestedReplicatePolicyRecord:
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


@define(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: str

    def __attrs_post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError("Lower bound cannot be greater than upper bound")

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@define(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: str = "two-sided"


@define(frozen=True, slots=True, kw_only=True)
class LinearRegressionResult:
    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


__all__ = [
    "BootstrapMethod",
    "ConfidenceInterval",
    "HypothesisTestResult",
    "LinearRegressionResult",
    "NestedReplicatePolicyRecord",
    "PairedSeedDifferenceRecord",
    "StatisticalMethod",
    "StatisticalProcedureError",
    "StatisticalProfileRecord",
]
