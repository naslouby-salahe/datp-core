"""Result records for cluster-stability analyses (ablation and membership variants)."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from attrs import define


class ClusterDispersionStatus(StrEnum):
    """Closed outcome of a within- or across-cluster dispersion computation.

    Distinguishes a genuinely computed value from every reason it can be unavailable, so an
    empty cluster or a client population lacking usable observations is never silently
    reported as a fabricated zero or a NaN.
    """

    AVAILABLE = "available"
    UNAVAILABLE_EMPTY_CLUSTER = "unavailable_empty_cluster"
    UNAVAILABLE_NO_AVAILABLE_FPR = "unavailable_no_available_fpr"
    UNAVAILABLE_INSUFFICIENT_OBSERVATIONS = "unavailable_insufficient_observations"
    UNAVAILABLE_INCOMPLETE_METRIC_POPULATION = "unavailable_incomplete_metric_population"
    UNAVAILABLE_NON_FINITE_INPUT = "unavailable_non_finite_input"


@define(frozen=True, slots=True, kw_only=True)
class ClusterDispersionResult:
    status: ClusterDispersionStatus
    value: float | None
    reason: str | None
    observed_cluster_count: int
    available_cluster_count: int
    excluded_client_count: int

    def __attrs_post_init__(self) -> None:
        if self.status is ClusterDispersionStatus.AVAILABLE and self.value is None:
            raise ValueError("An available cluster dispersion result must have a value")
        if self.status is not ClusterDispersionStatus.AVAILABLE and self.value is not None:
            raise ValueError(
                "An unavailable cluster dispersion result must not have a substitute value")


@define(frozen=True, slots=True, kw_only=True)
class ClusterAblationObservation:
    seed: int
    fingerprint_features: tuple[str, ...]
    adjusted_rand_index: float


@define(frozen=True, slots=True, kw_only=True)
class ClusterAblationStabilityResult:
    analysis_label: str
    comparison_unit: str
    reference_evaluation: str
    observations: tuple[ClusterAblationObservation, ...]


@define(frozen=True, slots=True, kw_only=True)
class ClusterStabilitySeedSummary:
    seed: int
    cluster_membership_per_client: Mapping[str, int]
    cluster_size: Mapping[str, int]
    singleton_cluster_flag: bool
    empty_cluster_flag: bool
    within_cluster_threshold_dispersion: ClusterDispersionResult
    within_cluster_fpr_dispersion: ClusterDispersionResult
    across_cluster_threshold_dispersion: ClusterDispersionResult
    across_cluster_mean_fpr_dispersion: ClusterDispersionResult


@define(frozen=True, slots=True, kw_only=True)
class ClusterMembershipStabilityResult:
    analysis_label: str
    comparison_unit: str
    seed_summaries: tuple[ClusterStabilitySeedSummary, ...]
    adjusted_rand_index: tuple[float, ...]
    mean_adjusted_rand_index: float | None


ClusterStabilityAnalysisResult = ClusterAblationStabilityResult | ClusterMembershipStabilityResult


__all__ = [
    "ClusterAblationObservation",
    "ClusterAblationStabilityResult",
    "ClusterDispersionResult",
    "ClusterDispersionStatus",
    "ClusterMembershipStabilityResult",
    "ClusterStabilityAnalysisResult",
    "ClusterStabilitySeedSummary",
]
