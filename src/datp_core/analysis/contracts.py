"""Cross-cutting analysis contracts shared by multiple unrelated capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from attrs import define

from datp_core.core.identifiers import ExperimentId, MetricId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates

if TYPE_CHECKING:
    from datp_core.core.freezing import FrozenResultManifest


@runtime_checkable
class QuantileThresholdPolicy(Protocol):
    """A threshold policy that exposes a quantile value.

    Replaces ``getattr(policy, "quantile", None)`` with typed structural matching.
    """

    quantile: float


@define(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    """A confidence interval with its construction method."""

    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: str

    def __attrs_post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"Confidence interval lower bound {self.lower_bound} exceeds upper bound {self.upper_bound}"
            )

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@define(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    """Result of a statistical hypothesis test."""

    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: str = "two-sided"


@define(frozen=True, slots=True, kw_only=True)
class LinearRegressionResult:
    """Simple linear regression with leverage diagnostics."""

    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    """One paired-seed statistical comparison between two threshold policies."""

    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


@define(frozen=True, slots=True, kw_only=True)
class PairedThresholdAnalysisResult:
    """Core paired-threshold comparison result used across all analysis capabilities."""

    analysis_label: str
    metric: str
    first_threshold_policy: str
    second_threshold_policy: str
    training_seeds: tuple[int, ...]
    first_seed_values: tuple[float, ...]
    second_seed_values: tuple[float, ...]
    first_mean: float
    second_mean: float
    mean_difference: float
    confidence_interval: ConfidenceInterval
    p_value: float | None
    rank_biserial: float | None
    resample_count: int
    analysis_seed: int
    seed_differences: tuple[float, ...]
    sign_consistency: float
    zero_difference_count: int
    negative_difference_count: int
    partition_condition: str | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    calibration_sample_count: int | None = None
    holm_adjusted_p_value: float | None = None


# ---------------------------------------------------------------------------
# Relocated from execution/inputs.py — typed artifact references and
# prerequisite results that belong to the analysis domain contract.
# ---------------------------------------------------------------------------


@define(frozen=True, slots=True, kw_only=True)
class AnalysisArtifactRef:
    """One direct upstream artifact with its complete producer coordinates."""

    coordinates: AnalysisInputCoordinates
    relative_path: str


@define(frozen=True, slots=True, kw_only=True)
class PrerequisiteExperimentResult:
    """A validated, immutable frozen result supplied by a configured prerequisite."""

    experiment_id: ExperimentId
    frozen_result_path: str
    frozen_result_checksum: str
    scientific_fingerprint: str
    result: FrozenResultManifest

    def paired_result(self, analysis_label: str) -> PairedThresholdAnalysisResult:
        """Return the unique paired result matching *analysis_label*."""
        from datp_core.analysis.runtime.codec import structure_paired_result

        matches = tuple(
            item
            for item in self.result.statistical_results
            if isinstance(item, dict) and item.get("analysis_label") == analysis_label and "seed_differences" in item
        )
        if len(matches) != 1:
            raise PrerequisiteResultMissingError(
                f"Prerequisite '{self.experiment_id.value}' has no unique paired result "
                f"for analysis '{analysis_label}'"
            )
        return structure_paired_result(matches[0])


# ---------------------------------------------------------------------------
# Errors imported late to avoid circular imports with the codec.
# ---------------------------------------------------------------------------


from datp_core.analysis.errors import PrerequisiteResultMissingError  # noqa: E402
