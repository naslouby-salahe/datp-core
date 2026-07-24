"""Result records for cluster-stability analyses (ablation and membership variants)."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define


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
    within_cluster_threshold_dispersion: float | None
    within_cluster_fpr_dispersion: float | None
    across_cluster_threshold_dispersion: float | None
    across_cluster_mean_fpr_dispersion: float | None


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
    "ClusterMembershipStabilityResult",
    "ClusterStabilityAnalysisResult",
    "ClusterStabilitySeedSummary",
]
