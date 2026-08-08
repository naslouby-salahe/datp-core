"""Data-driven client-cluster threshold construction."""

from dataclasses import dataclass
from typing import ClassVar, Literal

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.core.errors import ScientificContractError, require_contract
from datp_core.core.identifiers import ContractSubject, FederatedThresholdMethod
from datp_core.core.numeric import (
    ClusterIndex,
    DistributionSkewness,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    ScoreMoment,
    Seed,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    CANONICAL_QUANTILE,
    ClusterThresholdAggregation,
    ClusterThresholdProtocol,
    KMeansInitialization,
    LocalQuantile,
    ThresholdAssignment,
    mean_local_threshold,
    median_local_threshold,
    require_unique_clients,
    validate_assignments,
    validate_group_membership,
)
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, exact_empirical_quantile, local_quantile


@dataclass(frozen=True, slots=True)
class FingerprintFeatures:
    mean: ScoreMoment
    standard_deviation: ScoreMoment
    skewness: DistributionSkewness
    p95: ThresholdValue


@dataclass(frozen=True, slots=True)
class ClusterFingerprint:
    client: ClientIdentity
    raw: FingerprintFeatures
    standardized: FingerprintFeatures


@dataclass(frozen=True, slots=True)
class ClusterMembership:
    cluster_index: ClusterIndex
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    cluster_threshold: ThresholdValue | None
    threshold_aggregation: ClusterThresholdAggregation = (
        ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
    )

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
            match_message="contributing local quantile clients must exactly equal cluster members",
            threshold_message="cluster threshold must equal the declared local-threshold aggregation",
            expected_group_threshold=_aggregate_local_thresholds(
                self.contributing_local_quantiles,
                self.threshold_aggregation,
            ),
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
        require_unique_clients(tuple(item.client for item in self.fingerprints), "fingerprint")
        cluster_indices = tuple(item.cluster_index.value for item in self.clusters)
        expected_indices = frozenset(range(self.group_count.value))
        require_contract(
            frozenset(cluster_indices) == expected_indices and len(cluster_indices) == len(expected_indices),
            "cluster indices must equal exactly 0 through group_count minus one",
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
            len(frozenset(all_members)) == len(all_members),
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
            if cluster.cluster_threshold is not None
            for client in cluster.members
        )
        validate_assignments(
            self.assignments,
            expected_assignments,
            label="threshold assignments",
            mismatch_message="a cluster threshold assignment must use its cluster threshold",
        )
        require_contract(
            all((not cluster.members) == (cluster.cluster_threshold is None) for cluster in self.clusters),
            "empty clusters must omit thresholds and non-empty clusters must declare them",
            ContractSubject.THRESHOLD,
        )


def _sklearn_init(initialization: KMeansInitialization) -> Literal["k-means++"]:
    match initialization:
        case KMeansInitialization.KMEANS_PLUS_PLUS:
            return "k-means++"


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
    matrix = np.asarray(
        [
            (features.mean.value, features.standard_deviation.value, features.skewness.value, features.p95.value)
            for features in raw_features
        ],
        dtype=np.float64,
    )
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            "fingerprint matrix must be finite before scaling and clustering",
            subject=ContractSubject.THRESHOLD,
        )
    standardized_matrix = StandardScaler().fit_transform(matrix)
    labels = KMeans(
        n_clusters=protocol.group_count.value,
        init=_sklearn_init(protocol.initialization),
        n_init=protocol.initialization_count.value,
        max_iter=protocol.maximum_iterations.value,
        random_state=protocol.random_state.value,
    ).fit_predict(standardized_matrix)
    fingerprints = tuple(
        ClusterFingerprint(
            client=item.client,
            raw=raw,
            standardized=_as_fingerprint_features(standardized),
        )
        for item, raw, standardized in zip(ordered, raw_features, standardized_matrix, strict=True)
    )
    local_quantiles = tuple(local_quantile(item, protocol.quantile) for item in ordered)
    clusters, assignments = _build_clusters(
        ordered,
        labels,
        protocol.group_count,
        local_quantiles,
        protocol.threshold_aggregation,
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


def _as_fingerprint_features(row: np.ndarray) -> FingerprintFeatures:
    return FingerprintFeatures(
        mean=ScoreMoment(float(row[0])),
        standard_deviation=ScoreMoment(float(row[1])),
        skewness=DistributionSkewness(float(row[2])),
        p95=ThresholdValue(float(row[3])),
    )


def _raw_fingerprint(scores: np.ndarray) -> FingerprintFeatures:
    mean = float(np.mean(scores))
    standard_deviation = float(np.std(scores, ddof=0))
    if standard_deviation == 0.0 or np.ptp(scores) == 0.0:
        skewness_value = 0.0
    else:
        skewness_value = float(skew(scores, bias=True))
        if not np.isfinite(skewness_value):
            raise ScientificContractError(
                "fingerprint skewness must be finite",
                subject=ContractSubject.THRESHOLD,
            )
    return FingerprintFeatures(
        mean=ScoreMoment(mean),
        standard_deviation=ScoreMoment(standard_deviation),
        skewness=DistributionSkewness(skewness_value),
        p95=ThresholdValue(exact_empirical_quantile(scores, CANONICAL_QUANTILE).value),
    )


def _build_clusters(
    ordered: tuple[ClientBenignCalibrationScores, ...],
    labels: np.ndarray,
    group_count: GroupCount,
    local_quantiles: tuple[LocalQuantile, ...],
    aggregation: ClusterThresholdAggregation,
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
                    threshold_aggregation=aggregation,
                )
            )
            continue
        contributing = tuple(_local_quantile(local_quantiles, client) for client in members)
        cluster_value = _aggregate_local_thresholds(contributing, aggregation)
        clusters.append(
            ClusterMembership(
                cluster_index=cluster_index,
                members=members,
                contributing_local_quantiles=contributing,
                cluster_threshold=cluster_value,
                threshold_aggregation=aggregation,
            )
        )
        assignments.extend(ThresholdAssignment(client, cluster_value) for client in members)
    return tuple(clusters), tuple(assignments)


def _aggregate_local_thresholds(
    contributing: tuple[LocalQuantile, ...],
    aggregation: ClusterThresholdAggregation,
) -> ThresholdValue:
    match aggregation:
        case ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS:
            return mean_local_threshold(contributing)
        case ClusterThresholdAggregation.MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS:
            return median_local_threshold(contributing)
        case _:
            raise ScientificContractError(
                f"unsupported cluster threshold aggregation {aggregation}",
                subject=ContractSubject.THRESHOLD,
            )


def _cluster_members(
    ordered: tuple[ClientBenignCalibrationScores, ...],
    labels: np.ndarray,
    cluster_index: ClusterIndex,
) -> tuple[ClientIdentity, ...]:
    return tuple(
        item.client
        for item, label in zip(ordered, labels, strict=True)
        if label == cluster_index.value
    )


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
