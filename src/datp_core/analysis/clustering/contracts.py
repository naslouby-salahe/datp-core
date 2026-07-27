"""Clustering-specific analysis contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from datp_core.analysis._base import FrozenModel
from datp_core.analysis.enums import AnalysisResultKind, ClusterDispersionStatus
from datp_core.core.identifiers import AnalysisLabel, ClientId, ClusterLabel, EvaluationLabel
from datp_core.core.seeding import Seed


class ClientClusterMembership(FrozenModel):
    client_id: ClientId
    cluster_label: ClusterLabel


class ClusterSize(FrozenModel):
    cluster_label: ClusterLabel
    client_count: int


class ClusterDispersionResult(FrozenModel):
    status: ClusterDispersionStatus
    value: float | None
    reason: str | None
    observed_cluster_count: int
    available_cluster_count: int
    excluded_client_count: int


class ClusterAblationObservation(FrozenModel):
    seed: Seed
    fingerprint_features: tuple[str, ...]
    adjusted_rand_index: float


class ClusterAblationStabilityResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.CLUSTER_ABLATION] = AnalysisResultKind.CLUSTER_ABLATION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    comparison_unit: str
    reference_evaluation: EvaluationLabel
    observations: tuple[ClusterAblationObservation, ...]


class ClusterStabilitySeedSummary(FrozenModel):
    seed: Seed
    cluster_memberships: tuple[ClientClusterMembership, ...]
    cluster_sizes: tuple[ClusterSize, ...]
    singleton_cluster_flag: bool
    empty_cluster_flag: bool
    within_cluster_threshold_dispersion: ClusterDispersionResult
    within_cluster_fpr_dispersion: ClusterDispersionResult
    across_cluster_threshold_dispersion: ClusterDispersionResult
    across_cluster_mean_fpr_dispersion: ClusterDispersionResult


class ClusterMembershipStabilityResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.CLUSTER_STABILITY] = AnalysisResultKind.CLUSTER_STABILITY
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    comparison_unit: str
    seed_summaries: tuple[ClusterStabilitySeedSummary, ...]
    adjusted_rand_index: tuple[float, ...]
    mean_adjusted_rand_index: float | None


ClusterStabilityAnalysisResult = ClusterAblationStabilityResult | ClusterMembershipStabilityResult
