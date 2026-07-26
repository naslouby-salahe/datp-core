"""Cluster dispersion primitives: within-cluster, between-cluster, and ablation observations."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.contracts import ClusterDispersionResult
from datp_core.analysis.enums import ClusterDispersionKind, ClusterDispersionStatus
from datp_core.core.identifiers import ClusterLabel


def compute_adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    """Compute adjusted Rand index (ARI) between ground truth and predicted cluster labels."""
    return float(adjusted_rand_score(labels_true, labels_pred))


def cluster_dispersion(
    cluster_sizes: Mapping[ClusterLabel, int],
    value_groups: Mapping[ClusterLabel, Sequence[float]],
    *,
    kind: ClusterDispersionKind,
    metric_covered_clients: int | None = None,
    total_clients: int | None = None,
) -> ClusterDispersionResult:
    """Compute within- or across-cluster dispersion with typed unavailability reasons."""
    observed_cluster_count = len(cluster_sizes)
    non_empty_labels = sorted((label for label, size in cluster_sizes.items() if size > 0), key=lambda lbl: lbl.value)
    empty_labels = sorted((label for label, size in cluster_sizes.items() if size == 0), key=lambda lbl: lbl.value)

    if empty_labels:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_EMPTY_CLUSTER,
            value=None,
            reason=f"cluster(s) {[lbl.value for lbl in empty_labels]} have no assigned clients",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels),
            excluded_client_count=0,
        )
    if metric_covered_clients == 0 and total_clients:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_INCOMPLETE_METRIC_POPULATION,
            value=None,
            reason="no metric rows are available for any client in the threshold population",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=0,
            excluded_client_count=total_clients,
        )

    excluded_client_count = sum(cluster_sizes[label] - len(value_groups.get(label, ())) for label in non_empty_labels)
    no_value_labels = [label for label in non_empty_labels if not value_groups.get(label)]

    if no_value_labels:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_NO_AVAILABLE_FPR,
            value=None,
            reason=f"cluster(s) {[lbl.value for lbl in no_value_labels]} have no available false-positive-rate values",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels) - len(no_value_labels),
            excluded_client_count=excluded_client_count,
        )
    if kind == ClusterDispersionKind.ACROSS and len(non_empty_labels) < 2:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_INSUFFICIENT_OBSERVATIONS,
            value=None,
            reason="fewer than two clusters contribute values; across-cluster dispersion is undefined",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels),
            excluded_client_count=excluded_client_count,
        )

    if kind == ClusterDispersionKind.WITHIN:
        value = float(np.mean([np.std(value_groups[label]) for label in non_empty_labels]))
    else:
        value = float(np.std([np.mean(value_groups[label]) for label in non_empty_labels]))

    if not math.isfinite(value):
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_NON_FINITE_INPUT,
            value=None,
            reason="dispersion computation produced a non-finite value",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels),
            excluded_client_count=excluded_client_count,
        )

    return ClusterDispersionResult(
        status=ClusterDispersionStatus.AVAILABLE,
        value=value,
        reason=None,
        observed_cluster_count=observed_cluster_count,
        available_cluster_count=len(non_empty_labels),
        excluded_client_count=excluded_client_count,
    )
