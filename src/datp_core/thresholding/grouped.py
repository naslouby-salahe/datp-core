"""`CLUSTER_THRESHOLD`: locked four-feature benign-error fingerprint k-means grouping.

The fingerprint's `p95` feature is a fixed structural definition (always the 95th
percentile, independent of whatever quantile target an experiment selects for local
threshold construction), so it reuses the canonical quantile value object directly
rather than a second hardcoded literal.
"""

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import ClusterIndex, GroupCount, ThresholdValue
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.models import ClusterThresholdProtocol
from datp_core.thresholding.models import (
    ClusterFingerprint,
    ClusterMembership,
    GroupedThresholdResult,
    LocalQuantile,
    ThresholdAssignment,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    exact_empirical_quantile,
    local_quantile,
    unweighted_mean,
)


def _as_quadruple(row: np.ndarray) -> tuple[float, float, float, float]:
    return float(row[0]), float(row[1]), float(row[2]), float(row[3])


def _raw_fingerprint(scores: np.ndarray) -> tuple[float, float, float, float]:
    mean = float(np.mean(scores))
    standard_deviation = float(np.std(scores, ddof=0))
    if standard_deviation == 0.0 or np.ptp(scores) == 0.0:
        skewness = 0.0
    else:
        skewness = float(skew(scores, bias=True))
        if not np.isfinite(skewness):
            raise ScientificContractError(
                "fingerprint skewness must be finite", subject=ContractSubject.THRESHOLD
            )
    p95 = exact_empirical_quantile(scores, CANONICAL_QUANTILE).value
    return mean, standard_deviation, skewness, p95


def construct_grouped_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: ClusterThresholdProtocol,
) -> GroupedThresholdResult:
    if len(eligible) <= protocol.group_count.value:
        raise ScientificContractError(
            "grouped thresholding requires more eligible clients than the declared group count",
            subject=ContractSubject.THRESHOLD,
        )
    ordered = tuple(sorted(eligible, key=lambda item: item.client))
    raw_features = tuple(_raw_fingerprint(client_scores.as_array) for client_scores in ordered)
    matrix = np.asarray(raw_features, dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            "fingerprint matrix must be finite before scaling and clustering",
            subject=ContractSubject.THRESHOLD,
        )
    standardized_matrix = StandardScaler().fit_transform(matrix)

    kmeans = KMeans(
        n_clusters=protocol.group_count.value,
        init="k-means++",
        max_iter=protocol.maximum_iterations.value,
        random_state=protocol.random_state.value,
    )
    kmeans.set_params(n_init=protocol.initialization_count.value)
    labels = kmeans.fit_predict(standardized_matrix)

    fingerprints = tuple(
        ClusterFingerprint(
            client=client_scores.client,
            raw=raw_row,
            standardized=_as_quadruple(standardized_row),
        )
        for client_scores, raw_row, standardized_row in zip(ordered, raw_features, standardized_matrix, strict=True)
    )
    local_quantiles_by_client = {
        client_scores.client: local_quantile(client_scores, protocol.quantile) for client_scores in ordered
    }
    clusters, assignments = _build_clusters(ordered, labels, protocol.group_count, local_quantiles_by_client)

    return GroupedThresholdResult(
        method=protocol.method,
        coordinate=ordered[0].coordinate,
        fingerprints=fingerprints,
        clusters=clusters,
        assignments=assignments,
        initialization=protocol.initialization,
        initialization_count=protocol.initialization_count,
        maximum_iterations=protocol.maximum_iterations,
        random_state=protocol.random_state,
        group_count=protocol.group_count,
    )


def _cluster_members(
    ordered: tuple[ClientBenignCalibrationScores, ...], labels: np.ndarray, cluster_index: ClusterIndex
) -> tuple[ClientIdentity, ...]:
    members = tuple(
        client_scores.client
        for client_scores, label in zip(ordered, labels, strict=True)
        if label == cluster_index.value
    )
    if not members:
        raise ScientificContractError(
            "k-means produced an empty cluster; grouped thresholding requires every cluster to be non-empty",
            subject=ContractSubject.THRESHOLD,
        )
    return members


def _build_clusters(
    ordered: tuple[ClientBenignCalibrationScores, ...],
    labels: np.ndarray,
    group_count: GroupCount,
    local_quantiles_by_client: dict[ClientIdentity, LocalQuantile],
) -> tuple[tuple[ClusterMembership, ...], tuple[ThresholdAssignment, ...]]:
    clusters: list[ClusterMembership] = []
    assignments: list[ThresholdAssignment] = []
    for index in range(group_count.value):
        cluster_index = ClusterIndex(index)
        members = _cluster_members(ordered, labels, cluster_index)
        contributing = tuple(local_quantiles_by_client[client] for client in members)
        cluster_value = ThresholdValue(unweighted_mean(tuple(item.value.value for item in contributing)))
        clusters.append(
            ClusterMembership(
                cluster_index=cluster_index,
                members=members,
                contributing_local_quantiles=contributing,
                cluster_threshold=cluster_value,
            )
        )
        assignments.extend(ThresholdAssignment(client, cluster_value) for client in members)
    return tuple(clusters), tuple(assignments)
