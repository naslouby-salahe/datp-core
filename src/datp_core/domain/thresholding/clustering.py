from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from math import comb, isfinite
from re import fullmatch
from typing import Final

from datp_core.domain.artifacts.references import CONTENT_HASH_PATTERN, StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.seeds import Seed, SeedRole, derive_seed
from datp_core.domain.thresholding.policies import ThresholdPercentile, ThresholdValue

_POSITIVE_INTEGER_CONSTRAINT = "integer >= 1"


class B4FingerprintField(StrEnum):
    MEAN = "mean"
    STANDARD_DEVIATION = "std"
    SKEW = "skew"
    P95 = "p95"


class B4FingerprintScalerSpec(StrEnum):
    STANDARD_SCALER = "standard_scaler"


class B4FingerprintFitScope(StrEnum):
    ELIGIBLE_CLIENT_FINGERPRINTS = "eligible_client_fingerprints"


class B4ClusteringAlgorithm(StrEnum):
    KMEANS_PLUS_PLUS = "kmeans++"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterCount:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise DomainValidationError(
                detail="cluster count must be a positive integer",
                value=repr(self.value),
                constraint=_POSITIVE_INTEGER_CONSTRAINT,
            )


CANONICAL_CLUSTER_K: Final = ClusterCount(value=3)


def is_canonical_k(*, cluster_count: ClusterCount) -> bool:
    if type(cluster_count) is not ClusterCount:
        raise DomainValidationError(
            detail="canonical B4 cluster check requires a ClusterCount value object",
            value=repr(cluster_count),
            constraint="ClusterCount",
        )
    return cluster_count == CANONICAL_CLUSTER_K


@dataclass(frozen=True, slots=True, kw_only=True)
class KMeansInitializationCount:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise DomainValidationError(
                detail="KMeans initialization count must be a positive integer",
                value=repr(self.value),
                constraint=_POSITIVE_INTEGER_CONSTRAINT,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class KMeansMaximumIterations:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise DomainValidationError(
                detail="KMeans maximum iterations must be a positive integer",
                value=repr(self.value),
                constraint=_POSITIVE_INTEGER_CONSTRAINT,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class PinnedScikitLearnVersion:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str:
            raise DomainValidationError(
                detail="scikit-learn version must be an exact three-part numeric version",
                value=repr(self.value),
                constraint="major.minor.patch",
            )
        parts = self.value.split(".")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise DomainValidationError(
                detail="scikit-learn version must be an exact three-part numeric version",
                value=repr(self.value),
                constraint="major.minor.patch",
            )


CANONICAL_KMEANS_N_INIT: Final = KMeansInitializationCount(value=10)
CANONICAL_KMEANS_MAX_ITER: Final = KMeansMaximumIterations(value=300)
PINNED_SCIKIT_LEARN_VERSION: Final = PinnedScikitLearnVersion(value="1.9.0")


@dataclass(frozen=True, slots=True, kw_only=True)
class KMeansRandomState:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 0 <= self.value < 2**32:
            raise DomainValidationError(
                detail="KMeans random state must fit its exact integer domain",
                value=repr(self.value),
                constraint="integer in [0, 2**32)",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class B4ClusteringSpec:
    experiment_seed: Seed
    clustering_identity: StageFingerprint
    fingerprint_fields: tuple[B4FingerprintField, ...]
    scaler: B4FingerprintScalerSpec
    scaler_fit_scope: B4FingerprintFitScope
    algorithm: B4ClusteringAlgorithm
    cluster_count: ClusterCount
    n_init: KMeansInitializationCount
    max_iter: KMeansMaximumIterations
    random_state: KMeansRandomState
    scikit_learn_version: PinnedScikitLearnVersion

    def __init__(self, *, experiment_seed: Seed, clustering_identity: StageFingerprint) -> None:
        if type(experiment_seed) is not Seed or type(clustering_identity) is not StageFingerprint:
            raise DomainValidationError(
                detail="canonical B4 clustering requires typed seed and stage identity",
                value=repr((experiment_seed, clustering_identity)),
                constraint="Seed and StageFingerprint",
            )
        object.__setattr__(self, "experiment_seed", experiment_seed)
        object.__setattr__(self, "clustering_identity", clustering_identity)
        object.__setattr__(
            self,
            "fingerprint_fields",
            (
                B4FingerprintField.MEAN,
                B4FingerprintField.STANDARD_DEVIATION,
                B4FingerprintField.SKEW,
                B4FingerprintField.P95,
            ),
        )
        object.__setattr__(self, "scaler", B4FingerprintScalerSpec.STANDARD_SCALER)
        object.__setattr__(self, "scaler_fit_scope", B4FingerprintFitScope.ELIGIBLE_CLIENT_FINGERPRINTS)
        object.__setattr__(self, "algorithm", B4ClusteringAlgorithm.KMEANS_PLUS_PLUS)
        object.__setattr__(self, "cluster_count", CANONICAL_CLUSTER_K)
        object.__setattr__(self, "n_init", CANONICAL_KMEANS_N_INIT)
        object.__setattr__(self, "max_iter", CANONICAL_KMEANS_MAX_ITER)
        derived_seed = derive_seed(
            experiment_seed=experiment_seed,
            role=SeedRole.CLUSTERING,
            stage_fingerprint=clustering_identity,
        )
        object.__setattr__(
            self,
            "random_state",
            KMeansRandomState(value=derived_seed.value % (2**32)),
        )
        object.__setattr__(self, "scikit_learn_version", PINNED_SCIKIT_LEARN_VERSION)

    @property
    def is_canonical_k(self) -> bool:
        return is_canonical_k(cluster_count=self.cluster_count)


@dataclass(frozen=True, slots=True, kw_only=True)
class B4Fingerprint:
    mean: float
    standard_deviation: float
    skew: float
    p95: float

    def __post_init__(self) -> None:
        values = (self.mean, self.standard_deviation, self.skew, self.p95)
        if any(type(value) not in {int, float} or isinstance(value, bool) or not isfinite(value) for value in values):
            raise DomainValidationError(
                detail="B4 fingerprint values must be finite",
                value=repr(values),
                constraint="finite mean/std/skew/p95",
            )
        if self.standard_deviation < 0:
            raise DomainValidationError(
                detail="B4 fingerprint standard deviation must be non-negative",
                value=repr(self.standard_deviation),
                constraint="standard deviation >= 0",
            )

    @property
    def values(self) -> tuple[float, float, float, float]:
        return (self.mean, self.standard_deviation, self.skew, self.p95)


@dataclass(frozen=True, slots=True, kw_only=True)
class ScaledB4Fingerprint:
    mean: float
    standard_deviation: float
    skew: float
    p95: float

    def __post_init__(self) -> None:
        values = (self.mean, self.standard_deviation, self.skew, self.p95)
        if any(type(value) not in {int, float} or isinstance(value, bool) or not isfinite(value) for value in values):
            raise DomainValidationError(
                detail="scaled B4 fingerprint values must be finite",
                value=repr(values),
                constraint="finite scaled mean/std/skew/p95",
            )

    @property
    def values(self) -> tuple[float, float, float, float]:
        return (self.mean, self.standard_deviation, self.skew, self.p95)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterAssignmentEntry:
    client_id: ClientId
    cluster_index: int

    def __post_init__(self) -> None:
        if type(self.client_id) is not ClientId or type(self.cluster_index) is not int:
            raise DomainValidationError(
                detail="cluster assignment requires a typed client and integer cluster index",
                value=repr(self),
                constraint="ClientId and integer cluster index",
            )
        if not 0 <= self.cluster_index < CANONICAL_CLUSTER_K.value:
            raise DomainValidationError(
                detail="canonical B4 cluster index is outside the locked range",
                value=repr(self.cluster_index),
                constraint="0 <= cluster index < 3",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScaledFingerprintReference:
    client_id: ClientId
    fingerprint: ScaledB4Fingerprint

    def __post_init__(self) -> None:
        if type(self.client_id) is not ClientId or type(self.fingerprint) is not ScaledB4Fingerprint:
            raise DomainValidationError(
                detail="scaled fingerprint reference requires typed client and fingerprint",
                value=repr(self),
                constraint="ClientId and ScaledB4Fingerprint",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterCentroidReference:
    cluster_index: int
    fingerprint: ScaledB4Fingerprint

    def __post_init__(self) -> None:
        if type(self.cluster_index) is not int or not 0 <= self.cluster_index < CANONICAL_CLUSTER_K.value:
            raise DomainValidationError(
                detail="canonical B4 centroid requires an in-range integer cluster index",
                value=repr(self.cluster_index),
                constraint="0 <= cluster index < 3",
            )
        if type(self.fingerprint) is not ScaledB4Fingerprint:
            raise DomainValidationError(
                detail="cluster centroid requires a typed scaled fingerprint",
                value=repr(self.fingerprint),
                constraint="ScaledB4Fingerprint",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterAssignmentArtifact:
    clustering_identity: StageFingerprint
    assignments: tuple[ClusterAssignmentEntry, ...]
    scaled_fingerprints: tuple[ScaledFingerprintReference, ...]
    centroid_references: tuple[ClusterCentroidReference, ...]
    content_hash: str

    def __post_init__(self) -> None:
        assignment_clients = tuple(entry.client_id for entry in self.assignments)
        fingerprint_clients = tuple(entry.client_id for entry in self.scaled_fingerprints)
        if not _is_valid_cluster_assignment_artifact(self, assignment_clients, fingerprint_clients):
            raise DomainValidationError(
                detail="cluster assignment artifact requires canonical ordered matching assignment data",
                value=repr(self),
                constraint="typed identity, ordered matching clients, canonical centroids, and content hash",
            )


def _is_valid_cluster_assignment_artifact(
    artifact: ClusterAssignmentArtifact,
    assignment_clients: tuple[ClientId, ...],
    fingerprint_clients: tuple[ClientId, ...],
) -> bool:
    return all(
        (
            _has_valid_assignment_clients(artifact, assignment_clients, fingerprint_clients),
            _has_canonical_centroid_indexes(artifact.centroid_references),
            _is_content_hash(artifact.content_hash),
        )
    )


def _has_valid_assignment_clients(
    artifact: ClusterAssignmentArtifact,
    assignment_clients: tuple[ClientId, ...],
    fingerprint_clients: tuple[ClientId, ...],
) -> bool:
    return all(
        (
            type(artifact.clustering_identity) is StageFingerprint,
            bool(assignment_clients),
            assignment_clients == tuple(sorted(assignment_clients, key=lambda client: client.value)),
            len(set(assignment_clients)) == len(assignment_clients),
            fingerprint_clients == assignment_clients,
        )
    )


def _has_canonical_centroid_indexes(references: tuple[ClusterCentroidReference, ...]) -> bool:
    return tuple(reference.cluster_index for reference in references) == tuple(range(CANONICAL_CLUSTER_K.value))


def _is_content_hash(value: str) -> bool:
    return fullmatch(CONTENT_HASH_PATTERN, value) is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterThresholdAggregationSpec:
    percentile: ThresholdPercentile
    member_local_thresholds: tuple[ThresholdValue, ...]
    cluster_assignment_identity: StageFingerprint

    def __post_init__(self) -> None:
        if not _is_valid_cluster_threshold_aggregation(self):
            raise DomainValidationError(
                detail=(
                    "cluster threshold aggregation requires typed percentile, assignment identity, and local thresholds"
                ),
                value=repr(self),
                constraint="non-empty tuple of ThresholdValue with typed percentile and identity",
            )

    def aggregate(self) -> ThresholdValue:
        return ThresholdValue(
            value=sum(threshold.value for threshold in self.member_local_thresholds) / len(self.member_local_thresholds)
        )


def _is_valid_cluster_threshold_aggregation(specification: ClusterThresholdAggregationSpec) -> bool:
    return all(
        (
            type(specification.percentile) is ThresholdPercentile,
            type(specification.cluster_assignment_identity) is StageFingerprint,
            bool(specification.member_local_thresholds),
            all(type(value) is ThresholdValue for value in specification.member_local_thresholds),
        )
    )


def adjusted_rand_index(*, first: ClusterAssignmentArtifact, second: ClusterAssignmentArtifact) -> float:
    if not _has_matching_assignment_clients(first, second):
        raise DomainValidationError(
            detail="adjusted-Rand comparison requires identical ordered client membership",
            value=repr((first.assignments, second.assignments)),
            constraint="matching ordered assignment client ids",
        )
    first_labels = tuple(entry.cluster_index for entry in first.assignments)
    second_labels = tuple(entry.cluster_index for entry in second.assignments)
    agreements = _assignment_agreements(first_labels, second_labels)
    return _adjusted_rand_coefficient(first_labels, second_labels, agreements)


def _has_matching_assignment_clients(first: ClusterAssignmentArtifact, second: ClusterAssignmentArtifact) -> bool:
    return tuple(entry.client_id for entry in first.assignments) == tuple(
        entry.client_id for entry in second.assignments
    )


def _assignment_agreements(first_labels: tuple[int, ...], second_labels: tuple[int, ...]) -> tuple[int, int, int]:
    paired_counts = Counter(zip(first_labels, second_labels, strict=True))
    return (
        sum(comb(size, 2) for size in paired_counts.values()),
        sum(comb(size, 2) for size in Counter(first_labels).values()),
        sum(comb(size, 2) for size in Counter(second_labels).values()),
    )


def _adjusted_rand_coefficient(
    first_labels: tuple[int, ...],
    second_labels: tuple[int, ...],
    agreements: tuple[int, int, int],
) -> float:
    paired_agreement, first_agreement, second_agreement = agreements
    total_pairs = comb(len(first_labels), 2)
    if total_pairs == 0:
        return 1.0
    expected = first_agreement * second_agreement / total_pairs
    maximum = (first_agreement + second_agreement) / 2
    if maximum == expected:
        return _degenerate_adjusted_rand_value(first_labels, second_labels)
    return (paired_agreement - expected) / (maximum - expected)


def _degenerate_adjusted_rand_value(first_labels: tuple[int, ...], second_labels: tuple[int, ...]) -> float:
    if first_labels == second_labels:
        return 1.0
    return 0.0
