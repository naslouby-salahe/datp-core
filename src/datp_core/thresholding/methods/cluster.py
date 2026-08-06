"""Cluster threshold construction and persisted result contracts."""

import math
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    ContractSubject,
    FederatedThresholdMethod,
)
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values.counts import (
    ClusterIndex,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    Seed,
)
from datp_core.domain.values.ratios import ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.calibration import CANONICAL_QUANTILE, ClusterThresholdProtocol, KMeansInitialization
from datp_core.thresholding.assignments import (
    LocalQuantile,
    ThresholdAssignment,
    require_unique_clients,
    validate_assignments,
    validate_group_membership,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    exact_empirical_quantile,
    local_quantile,
    unweighted_mean,
)


@dataclass(frozen=True, slots=True)
class ClusterFingerprint:
    client: ClientIdentity
    raw: tuple[float, float, float, float]
    standardized: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        require_contract(
            len(self.raw) == 4 and len(self.standardized) == 4,
            "a cluster fingerprint must carry exactly mean, standard deviation, skewness, and p95",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            all(math.isfinite(value) for value in self.raw),
            "every raw fingerprint feature must be finite",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            all(math.isfinite(value) for value in self.standardized),
            "every standardized fingerprint feature must be finite",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ClusterMembership:
    cluster_index: ClusterIndex
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    cluster_threshold: ThresholdValue | None

    def __post_init__(self) -> None:
        if not self.members:
            require_contract(
                self.cluster_threshold is None and not self.contributing_local_quantiles,
                "empty cluster memberships cannot carry thresholds or quantiles",
                ContractSubject.THRESHOLD,
            )
            return
        if self.cluster_threshold is None:
            raise ScientificContractError(
                "non-empty cluster membership requires a cluster threshold",
                subject=ContractSubject.THRESHOLD,
            )
        validate_group_membership(
            self.members,
            self.contributing_local_quantiles,
            self.cluster_threshold,
            members_label="cluster members",
            match_message=("contributing local quantile clients must exactly equal cluster members"),
            threshold_message=("cluster_threshold must equal the unweighted mean of contributing local quantiles"),
        )


@dataclass(frozen=True, slots=True)
class GroupedThresholdResult:
    coordinate: FederatedTrainingCoordinate
    fingerprints: tuple[ClusterFingerprint, ...]
    clusters: tuple[ClusterMembership, ...]
    assignments: tuple[ThresholdAssignment, ...]
    initialization: KMeansInitialization
    initialization_count: KMeansInitializationCount
    maximum_iterations: KMeansMaximumIterationCount
    random_state: Seed
    group_count: GroupCount
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.CLUSTER_THRESHOLD

    def __post_init__(self) -> None:
        require_contract(
            len(self.clusters) == self.group_count.value,
            "the number of clusters must equal the declared group count",
            ContractSubject.THRESHOLD,
        )
        require_unique_clients(
            tuple(item.client for item in self.fingerprints),
            "fingerprint",
        )
        cluster_indices = tuple(item.cluster_index.value for item in self.clusters)
        expected_indices = set(range(self.group_count.value))
        require_contract(
            set(cluster_indices) == expected_indices and len(cluster_indices) == len(expected_indices),
            "cluster indices must equal exactly 0..group_count.value - 1",
            ContractSubject.THRESHOLD,
        )
        for cluster in self.clusters:
            for item in cluster.contributing_local_quantiles:
                require_contract(
                    item.coordinate == self.coordinate,
                    "every nested quantile must carry the containing result coordinate",
                    ContractSubject.COORDINATE,
                )
        all_members = tuple(client for cluster in self.clusters for client in cluster.members)
        require_contract(
            len(set(all_members)) == len(all_members),
            "a client cannot belong to more than one cluster",
            ContractSubject.CLIENT_IDENTITY,
        )
        require_contract(
            frozenset(all_members) == frozenset(item.client for item in self.fingerprints),
            "cluster membership must cover exactly the fingerprinted client set",
            ContractSubject.CLIENT_IDENTITY,
        )
        expected_assignments = tuple(
            ThresholdAssignment(client, cluster.cluster_threshold)
            for cluster in self.clusters
            for client in cluster.members
            if cluster.cluster_threshold is not None
        )
        validate_assignments(
            self.assignments,
            expected_assignments,
            label="threshold assignments",
            mismatch_message=("a cluster threshold assignment must use its cluster's threshold"),
        )
        require_contract(
            all((not cluster.members) == (cluster.cluster_threshold is None) for cluster in self.clusters),
            "empty clusters must omit thresholds; non-empty clusters must declare them",
            ContractSubject.THRESHOLD,
        )


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
    raw_features = tuple(_raw_fingerprint(item.as_array) for item in ordered)
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
            client=item.client,
            raw=raw,
            standardized=_as_quadruple(standardized),
        )
        for item, raw, standardized in zip(
            ordered,
            raw_features,
            standardized_matrix,
            strict=True,
        )
    )
    local_quantiles = tuple(local_quantile(item, protocol.quantile) for item in ordered)
    clusters, assignments = _build_clusters(
        ordered,
        labels,
        protocol.group_count,
        local_quantiles,
    )
    return GroupedThresholdResult(
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


def _as_quadruple(
    row: np.ndarray,
) -> tuple[float, float, float, float]:
    return float(row[0]), float(row[1]), float(row[2]), float(row[3])


def _raw_fingerprint(
    scores: np.ndarray,
) -> tuple[float, float, float, float]:
    mean = float(np.mean(scores))
    standard_deviation = float(np.std(scores, ddof=0))
    if standard_deviation == 0.0 or np.ptp(scores) == 0.0:
        skewness = 0.0
    else:
        skewness = float(skew(scores, bias=True))
        if not np.isfinite(skewness):
            raise ScientificContractError(
                "fingerprint skewness must be finite",
                subject=ContractSubject.THRESHOLD,
            )
    p95 = exact_empirical_quantile(scores, CANONICAL_QUANTILE).value
    return mean, standard_deviation, skewness, p95


def _build_clusters(
    ordered: tuple[ClientBenignCalibrationScores, ...],
    labels: np.ndarray,
    group_count: GroupCount,
    local_quantiles: tuple[LocalQuantile, ...],
) -> tuple[tuple[ClusterMembership, ...], tuple[ThresholdAssignment, ...]]:
    clusters: list[ClusterMembership] = []
    assignments: list[ThresholdAssignment] = []
    for index in range(group_count.value):
        cluster_index = ClusterIndex(index)
        members = _cluster_members(ordered, labels, cluster_index)
        if not members:
            clusters.append(
                ClusterMembership(
                    cluster_index=cluster_index,
                    members=(),
                    contributing_local_quantiles=(),
                    cluster_threshold=None,
                )
            )
            continue
        contributing = tuple(_local_quantile(local_quantiles, client) for client in members)
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


def _cluster_members(
    ordered: tuple[ClientBenignCalibrationScores, ...],
    labels: np.ndarray,
    cluster_index: ClusterIndex,
) -> tuple[ClientIdentity, ...]:
    """Return members for a declared cluster index.

    Empty memberships are preserved as explicit negative evidence rather than
    aborting construction before the evidence layer can record the outcome.
    """
    return tuple(item.client for item, label in zip(ordered, labels, strict=True) if label == cluster_index.value)


def _local_quantile(
    quantiles: tuple[LocalQuantile, ...],
    client: ClientIdentity,
) -> LocalQuantile:
    matches = tuple(item for item in quantiles if item.client == client)
    if len(matches) != 1:
        raise ScientificContractError(
            "cluster member must resolve exactly once in local quantiles",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]
