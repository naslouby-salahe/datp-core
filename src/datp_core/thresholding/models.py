"""Typed, discriminated federated threshold-construction results."""

import math
from dataclasses import dataclass
from enum import StrEnum
from statistics import fmean
from typing import ClassVar

from datp_core.domain.enums import (
    AvailabilityStatus,
    ContractSubject,
    FederatedThresholdMethod,
    KMeansInitialization,
    QuantileInterpolationSemantics,
)
from datp_core.domain.errors import require_contract
from datp_core.domain.values import (
    ByteCount,
    Checksum,
    ClusterIndex,
    ConformalRankIndex,
    CoverageTarget,
    FamilyIdentity,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    Quantile,
    Ratio,
    RowCount,
    ScoreValue,
    Seed,
    ShrinkageWeight,
    SummaryCoefficient,
    ThresholdValue,
    floats_absolutely_close,
    floats_exactly_equal,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import FRACTION_TOTAL_ABSOLUTE_TOLERANCE


def _mean_threshold(quantiles: tuple["LocalQuantile", ...]) -> float:
    return fmean(item.value.value for item in quantiles)


def _require_unique_clients(clients: tuple[ClientIdentity, ...], label: str) -> None:
    require_contract(
        len(set(clients)) == len(clients),
        f"{label} must have unique client identities",
        ContractSubject.CLIENT_IDENTITY,
    )


def _validate_local_quantiles(
    quantiles: tuple["LocalQuantile", ...], coordinate: FederatedTrainingCoordinate, *, label: str
) -> None:
    msg = (
        "shared threshold construction requires at least one contributing local quantile"
        if label == "contributing local quantiles"
        else "local threshold construction requires at least one eligible client"
    )
    require_contract(bool(quantiles), msg, ContractSubject.THRESHOLD)
    _require_unique_clients(tuple(item.client for item in quantiles), label)
    for item in quantiles:
        require_contract(
            item.coordinate == coordinate,
            "every nested quantile must carry the containing result coordinate",
            ContractSubject.COORDINATE,
        )


def _validate_assignments(
    assignments: tuple["ThresholdAssignment", ...],
    expected_pairs: tuple[tuple[ClientIdentity, ThresholdValue], ...],
    *,
    label: str,
    mismatch_message: str,
) -> None:
    assigned_clients = tuple(a.client for a in assignments)
    _require_unique_clients(assigned_clients, label)
    expected_clients = tuple(pair[0] for pair in expected_pairs)
    _require_unique_clients(expected_clients, "expected clients")
    require_contract(
        frozenset(assigned_clients) == frozenset(expected_clients),
        "threshold assignments must cover exactly the contributing client set",
        ContractSubject.CLIENT_IDENTITY,
    )
    actual_pairs = frozenset((a.client, a.threshold) for a in assignments)
    require_contract(actual_pairs == frozenset(expected_pairs), mismatch_message, ContractSubject.THRESHOLD)


def _validate_normalized_weights(weights: tuple[float, ...], expected_count: int) -> None:
    require_contract(
        len(weights) == expected_count,
        "one normalized weight is required per contributing local quantile",
        ContractSubject.THRESHOLD,
    )
    require_contract(all(w >= 0 for w in weights), "normalized weights must be non-negative", ContractSubject.THRESHOLD)
    require_contract(
        floats_absolutely_close(sum(weights), 1.0, FRACTION_TOTAL_ABSOLUTE_TOLERANCE),
        "normalized weights must sum to one",
        ContractSubject.THRESHOLD,
    )


def _validate_group_membership(
    members: tuple[ClientIdentity, ...],
    contributing_local_quantiles: tuple["LocalQuantile", ...],
    group_threshold: ThresholdValue,
    *,
    members_label: str,
    match_message: str,
) -> None:
    _require_unique_clients(members, members_label)
    quantile_clients = tuple(item.client for item in contributing_local_quantiles)
    _require_unique_clients(quantile_clients, "contributing local quantiles")
    require_contract(frozenset(quantile_clients) == frozenset(members), match_message, ContractSubject.CLIENT_IDENTITY)
    msg = (
        "family_threshold must equal the unweighted mean of contributing local quantiles"
        if "family" in match_message
        else "cluster_threshold must equal the unweighted mean of contributing local quantiles"
    )
    require_contract(
        floats_exactly_equal(group_threshold.value, _mean_threshold(contributing_local_quantiles)),
        msg,
        ContractSubject.THRESHOLD,
    )


def _validate_client_partition(
    eligible_clients: tuple[ClientIdentity, ...],
    assigned_clients: tuple[ClientIdentity, ...],
    unavailable_clients: tuple[ClientIdentity, ...],
) -> None:
    _require_unique_clients(eligible_clients, "eligible clients")
    _require_unique_clients(assigned_clients, "conformal assignments")
    _require_unique_clients(unavailable_clients, "unavailable clients")
    assigned_set, unavailable_set = frozenset(assigned_clients), frozenset(unavailable_clients)
    require_contract(
        not (assigned_set & unavailable_set),
        "a client cannot be both assigned and unavailable",
        ContractSubject.CLIENT_IDENTITY,
    )
    require_contract(
        (assigned_set | unavailable_set) == frozenset(eligible_clients),
        "assigned and unavailable clients must exactly cover the eligible client set",
        ContractSubject.CLIENT_IDENTITY,
    )


class ThresholdInfeasibilityReason(StrEnum):
    """Closed reasons a requested federated threshold method cannot be executed."""

    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = "size_aware_shrinkage_function_unresolved"
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = "group_count_exceeds_eligible_population"


@dataclass(frozen=True, slots=True)
class ThresholdDiagnostic:
    """Shared provenance and boundary-condition record attached to a quantile computation."""

    quantile_interpolation: QuantileInterpolationSemantics | None
    score_set_checksum: Checksum
    calibration_manifest_checksum: Checksum
    tie_count: RowCount
    availability: AvailabilityStatus


@dataclass(frozen=True, slots=True)
class LocalQuantile:
    """One client's exact empirical benign calibration quantile."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    value: ThresholdValue
    calibration_count: RowCount
    diagnostic: ThresholdDiagnostic

    def __post_init__(self) -> None:
        require_contract(
            self.calibration_count.value >= 1,
            "a local quantile requires at least one benign calibration score",
            ContractSubject.CALIBRATION,
        )


@dataclass(frozen=True, slots=True)
class ThresholdAssignment:
    """One client's assigned operating threshold."""

    client: ClientIdentity
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True)
class SharedThresholdResult:
    """`SHARED_THRESHOLD`: the unweighted mean of eligible local quantiles."""

    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SHARED_THRESHOLD

    def __post_init__(self) -> None:
        _validate_local_quantiles(
            self.contributing_local_quantiles, self.coordinate, label="contributing local quantiles"
        )
        _validate_assignments(
            self.assignments,
            tuple((item.client, self.shared_threshold) for item in self.contributing_local_quantiles),
            label="threshold assignments",
            mismatch_message="every assignment in a shared threshold result must carry the identical shared value",
        )
        require_contract(
            floats_exactly_equal(self.shared_threshold.value, _mean_threshold(self.contributing_local_quantiles)),
            "shared_threshold must equal the unweighted mean of contributing local quantiles",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class PooledSharedQuantileResult:
    """`POOLED_SHARED_QUANTILE`: the exact pooled benign quantile."""

    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    pooled_benign_score_count: RowCount
    diagnostic: ThresholdDiagnostic
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.POOLED_SHARED_QUANTILE

    def __post_init__(self) -> None:
        require_contract(
            self.pooled_benign_score_count.value >= 1,
            "pooled shared quantile requires at least one pooled benign score",
            ContractSubject.CALIBRATION,
        )
        _require_unique_clients(tuple(a.client for a in self.assignments), "pooled shared quantile assignments")
        require_contract(
            bool(self.assignments),
            "a shared threshold result requires at least one client assignment",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            all(floats_exactly_equal(a.threshold.value, self.shared_threshold.value) for a in self.assignments),
            "every assignment in a shared threshold result must carry the identical shared value",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class SampleWeightedSharedThresholdResult:
    """`SAMPLE_WEIGHTED_SHARED_THRESHOLD`: local quantiles weighted by benign calibration support."""

    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    normalized_weights: tuple[float, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD

    def __post_init__(self) -> None:
        _validate_normalized_weights(self.normalized_weights, len(self.contributing_local_quantiles))
        _validate_local_quantiles(
            self.contributing_local_quantiles, self.coordinate, label="contributing local quantiles"
        )
        _validate_assignments(
            self.assignments,
            tuple((item.client, self.shared_threshold) for item in self.contributing_local_quantiles),
            label="threshold assignments",
            mismatch_message="every assignment in a shared threshold result must carry the identical shared value",
        )
        expected_shared = sum(
            item.value.value * w
            for item, w in zip(self.contributing_local_quantiles, self.normalized_weights, strict=True)
        )
        require_contract(
            floats_exactly_equal(self.shared_threshold.value, expected_shared),
            "shared_threshold must equal the declared normalized weighted mean of contributing local quantiles",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class LocalThresholdResult:
    """`LOCAL_THRESHOLD`: each eligible client keeps its own benign calibration quantile."""

    coordinate: FederatedTrainingCoordinate
    local_quantiles: tuple[LocalQuantile, ...]
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_THRESHOLD

    def __post_init__(self) -> None:
        _validate_local_quantiles(self.local_quantiles, self.coordinate, label="local quantiles")
        _validate_assignments(
            self.assignments,
            tuple((item.client, item.value) for item in self.local_quantiles),
            label="threshold assignments",
            mismatch_message="a local threshold assignment must equal the client's own local quantile",
        )


@dataclass(frozen=True, slots=True)
class FamilyMembership:
    """One device-family group's threshold construction outcome."""

    family_id: FamilyIdentity
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    status: AvailabilityStatus
    family_threshold: ThresholdValue | None

    def __post_init__(self) -> None:
        is_available = self.status is AvailabilityStatus.AVAILABLE
        has_support = bool(self.members) and self.family_threshold is not None
        has_leftover = bool(self.members) or self.family_threshold is not None
        require_contract(
            not is_available or has_support,
            "an available family requires eligible members and a constructed threshold",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            is_available or not has_leftover,
            "an unavailable family must carry no members and no threshold",
            ContractSubject.THRESHOLD,
        )
        _require_unique_clients(self.members, "family members")
        quantile_clients = tuple(item.client for item in self.contributing_local_quantiles)
        _require_unique_clients(quantile_clients, "contributing local quantiles")
        if self.members or quantile_clients:
            require_contract(
                frozenset(quantile_clients) == frozenset(self.members),
                "contributing local quantile clients must exactly match declared family members",
                ContractSubject.CLIENT_IDENTITY,
            )
        if is_available and self.family_threshold is not None:
            require_contract(
                floats_exactly_equal(self.family_threshold.value, _mean_threshold(self.contributing_local_quantiles)),
                "family_threshold must equal the unweighted mean of contributing local quantiles",
                ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class FamilyThresholdResult:
    """`FAMILY_THRESHOLD`: mean of eligible local thresholds within each device family."""

    coordinate: FederatedTrainingCoordinate
    families: tuple[FamilyMembership, ...]
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.FAMILY_THRESHOLD

    def __post_init__(self) -> None:
        require_contract(
            bool(self.families),
            "family threshold construction requires at least one declared family",
            ContractSubject.THRESHOLD,
        )
        family_ids = tuple(f.family_id for f in self.families)
        require_contract(
            len(set(family_ids)) == len(family_ids), "family identities must be unique", ContractSubject.THRESHOLD
        )
        for family in self.families:
            for item in family.contributing_local_quantiles:
                require_contract(
                    item.coordinate == self.coordinate,
                    "every nested quantile must carry the containing result coordinate",
                    ContractSubject.COORDINATE,
                )
        expected_pairs = tuple(
            (client, family.family_threshold)
            for family in self.families
            if family.status is AvailabilityStatus.AVAILABLE and family.family_threshold is not None
            for client in family.members
        )
        _validate_assignments(
            self.assignments,
            expected_pairs,
            label="threshold assignments",
            mismatch_message="a family threshold assignment must use its family's constructed threshold",
        )


@dataclass(frozen=True, slots=True)
class ClusterFingerprint:
    """Locked four-feature benign reconstruction-error fingerprint for one client."""

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
            all(math.isfinite(v) for v in self.raw),
            "every raw fingerprint feature must be finite",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            all(math.isfinite(v) for v in self.standardized),
            "every standardized fingerprint feature must be finite",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ClusterMembership:
    """One k-means cluster's member set and aggregated threshold."""

    cluster_index: ClusterIndex
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    cluster_threshold: ThresholdValue

    def __post_init__(self) -> None:
        require_contract(
            bool(self.members), "a cluster membership requires at least one member", ContractSubject.THRESHOLD
        )
        _validate_group_membership(
            self.members,
            self.contributing_local_quantiles,
            self.cluster_threshold,
            members_label="cluster members",
            match_message="contributing local quantile clients must exactly equal cluster members",
        )


@dataclass(frozen=True, slots=True)
class GroupedThresholdResult:
    """`CLUSTER_THRESHOLD`: locked benign-error fingerprint k-means grouping."""

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
        _require_unique_clients(tuple(fp.client for fp in self.fingerprints), "fingerprint")
        cluster_indices = tuple(c.cluster_index.value for c in self.clusters)
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
            frozenset(all_members) == frozenset(fp.client for fp in self.fingerprints),
            "cluster membership must cover exactly the fingerprinted client set",
            ContractSubject.CLIENT_IDENTITY,
        )
        expected_pairs = tuple(
            (client, cluster.cluster_threshold) for cluster in self.clusters for client in cluster.members
        )
        _validate_assignments(
            self.assignments,
            expected_pairs,
            label="threshold assignments",
            mismatch_message="a cluster threshold assignment must use its cluster's threshold",
        )


@dataclass(frozen=True, slots=True)
class ShrinkageAssignment:
    """One client's blended threshold at one fixed shrinkage weight."""

    client: ClientIdentity
    lambda_weight: ShrinkageWeight
    local_threshold: ThresholdValue
    shared_threshold: ThresholdValue
    blended_threshold: ThresholdValue

    def __post_init__(self) -> None:
        expected = (
            self.lambda_weight.value * self.local_threshold.value
            + (1 - self.lambda_weight.value) * self.shared_threshold.value
        )
        require_contract(
            floats_exactly_equal(self.blended_threshold.value, expected),
            "blended threshold must equal lambda * local + (1 - lambda) * shared",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ShrinkageThresholdResult:
    """`LOCAL_GLOBAL_SHRINKAGE`: the complete fixed lambda-curve of blended thresholds."""

    coordinate: FederatedTrainingCoordinate
    weights: tuple[ShrinkageWeight, ...]
    assignments: tuple[ShrinkageAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE

    def __post_init__(self) -> None:
        require_contract(
            bool(self.weights),
            "shrinkage construction requires at least one declared lambda",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            len(set(self.weights)) == len(self.weights),
            "declared shrinkage weights must be unique",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            bool(self.assignments),
            "shrinkage construction requires at least one client assignment",
            ContractSubject.THRESHOLD,
        )
        declared_weights = set(self.weights)
        for a in self.assignments:
            require_contract(
                a.lambda_weight in declared_weights,
                "every shrinkage assignment must use a declared lambda weight",
                ContractSubject.THRESHOLD,
            )
        actual_keys = tuple((a.client, a.lambda_weight) for a in self.assignments)
        require_contract(
            len(set(actual_keys)) == len(actual_keys),
            "exactly one shrinkage assignment is required per (client, lambda_weight) pair",
            ContractSubject.THRESHOLD,
        )
        clients = frozenset(a.client for a in self.assignments)
        for weight in self.weights:
            observed = frozenset(a.client for a in self.assignments if a.lambda_weight == weight)
            require_contract(
                observed == clients,
                "every declared lambda must be evaluated for exactly the same client set",
                ContractSubject.THRESHOLD,
            )
        require_contract(
            len(self.assignments) == len(clients) * len(self.weights),
            "every declared (client, lambda_weight) combination must exist exactly once",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ConformalAssignment:
    """One client's finite-sample local conformal threshold."""

    client: ClientIdentity
    calibration_count: RowCount
    rank_index: ConformalRankIndex
    effective_quantile: Quantile
    selected_score: ScoreValue
    tie_count: RowCount
    threshold: ThresholdValue

    def __post_init__(self) -> None:
        require_contract(
            isinstance(self.rank_index, ConformalRankIndex),
            "conformal rank index must use the typed rank contract",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            self.rank_index.value <= self.calibration_count.value,
            "conformal rank index must fall within the calibration sample",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            floats_exactly_equal(self.threshold.value, self.selected_score.value),
            "conformal threshold value must equal the selected score",
            ContractSubject.THRESHOLD,
        )
        expected_quantile = self.rank_index.value / self.calibration_count.value
        require_contract(
            floats_absolutely_close(
                self.effective_quantile.value,
                expected_quantile,
                FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
            ),
            "conformal effective quantile must equal rank_index / calibration_count",
            ContractSubject.THRESHOLD,
        )

@dataclass(frozen=True, slots=True)
class ConformalThresholdResult:
    """`LOCAL_CONFORMAL_THRESHOLD`: finite-sample local conformal thresholds."""

    coordinate: FederatedTrainingCoordinate
    coverage: CoverageTarget
    eligible_clients: tuple[ClientIdentity, ...]
    assignments: tuple[ConformalAssignment, ...]
    unavailable_clients: tuple[ClientIdentity, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD

    def __post_init__(self) -> None:
        require_contract(
            bool(self.assignments),
            "a conformal threshold result requires at least one assigned client",
            ContractSubject.THRESHOLD,
        )
        _validate_client_partition(
            self.eligible_clients, tuple(a.client for a in self.assignments), self.unavailable_clients
        )

    @property
    def significance(self) -> Ratio:
        """Conformal miscoverage derived from the single authoritative coverage target."""
        return Ratio(1.0 - self.coverage.value)


@dataclass(frozen=True, slots=True)
class ClientBenignSummary:
    """Benign-only summary statistics one client may communicate: count, mean, variance."""

    client: ClientIdentity
    count: RowCount
    mean: float
    variance: float
    benign_exceedance_count: RowCount | None

    def __post_init__(self) -> None:
        require_contract(
            self.count.value >= 1,
            "a benign summary requires at least one calibration score",
            ContractSubject.CALIBRATION,
        )
        require_contract(self.variance >= 0, "variance must be non-negative", ContractSubject.THRESHOLD)
        require_contract(math.isfinite(self.mean), "summary mean must be finite", ContractSubject.THRESHOLD)
        require_contract(math.isfinite(self.variance), "summary variance must be finite", ContractSubject.THRESHOLD)
        if self.benign_exceedance_count is not None:
            require_contract(
                self.benign_exceedance_count.value <= self.count.value,
                "benign exceedance count cannot exceed calibration score count",
                ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class PooledVarianceDecomposition:
    """Between/within decomposition of the pooled benign score variance."""

    global_mean: float
    within_client_variance: float
    between_client_variance: float
    full_pooled_variance: float
    between_ratio: Ratio | None

    def __post_init__(self) -> None:
        require_contract(
            self.within_client_variance >= 0, "within-client variance must be non-negative", ContractSubject.THRESHOLD
        )
        require_contract(
            self.between_client_variance >= 0, "between-client variance must be non-negative", ContractSubject.THRESHOLD
        )
        require_contract(
            floats_exactly_equal(self.full_pooled_variance, self.within_client_variance + self.between_client_variance),
            "the full pooled variance must equal within-client plus between-client variance",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            math.isfinite(self.global_mean), "decomposition global mean must be finite", ContractSubject.THRESHOLD
        )
        require_contract(
            math.isfinite(self.full_pooled_variance),
            "decomposition full pooled variance must be finite",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class CentralizedAttainmentDiagnostic:
    """Centralized oracle attainment diagnostic computed from full pooled raw scores."""

    target_exceedance: Quantile
    achieved_exceedance: Ratio
    signed_attainment_error: float
    absolute_attainment_error: Ratio
    absolute_threshold_error_vs_pooled_quantile: float
    relative_threshold_error_vs_pooled_quantile: float | None

    def __post_init__(self) -> None:
        require_contract(
            math.isfinite(self.signed_attainment_error)
            and math.isfinite(self.absolute_threshold_error_vs_pooled_quantile)
            and (
                self.relative_threshold_error_vs_pooled_quantile is None
                or math.isfinite(self.relative_threshold_error_vs_pooled_quantile)
            ),
            "every numeric field in attainment diagnostic must be finite",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            floats_exactly_equal(
                self.signed_attainment_error, self.achieved_exceedance.value - self.target_exceedance.value
            ),
            "signed attainment error must equal achieved_exceedance - target_exceedance",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            floats_exactly_equal(self.absolute_attainment_error.value, abs(self.signed_attainment_error)),
            "absolute attainment error must equal abs(signed_attainment_error)",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            self.absolute_threshold_error_vs_pooled_quantile >= 0,
            "absolute threshold error must be non-negative",
            ContractSubject.THRESHOLD,
        )
        if self.relative_threshold_error_vs_pooled_quantile is not None:
            require_contract(
                self.relative_threshold_error_vs_pooled_quantile >= 0,
                "relative threshold error must be non-negative when present",
                ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class FixedCoefficientResult:
    """One supplementary sensitivity point on the fixed-coefficient curve."""

    coefficient: SummaryCoefficient
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True)
class FederatedStatisticsThresholdResult:
    """`FEDERATED_BENIGN_STATISTICS`: federated benign summary-statistics comparator."""

    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    client_summaries: tuple[ClientBenignSummary, ...]
    decomposition: PooledVarianceDecomposition
    matched_threshold: ThresholdValue
    centralized_attainment_diagnostic: CentralizedAttainmentDiagnostic
    centralized_pooled_quantile_diagnostic: ThresholdValue
    fixed_coefficient_curve: tuple[FixedCoefficientResult, ...]
    assignments: tuple[ThresholdAssignment, ...]
    estimated_communication_bytes: ByteCount
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS

    def __post_init__(self) -> None:
        require_contract(
            bool(self.client_summaries),
            "the federated benign-statistics comparator requires at least one client summary",
            ContractSubject.THRESHOLD,
        )
        summary_clients = tuple(s.client for s in self.client_summaries)
        _require_unique_clients(summary_clients, "client summaries")
        _validate_assignments(
            self.assignments,
            tuple((c, self.matched_threshold) for c in summary_clients),
            label="threshold assignments",
            mismatch_message="every assignment in a shared threshold result must carry the identical shared value",
        )


@dataclass(frozen=True, slots=True)
class ThresholdUnavailableResult:
    """A requested federated threshold method that cannot be executed, with a typed reason."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    reason: ThresholdInfeasibilityReason
    detail: str

    def __post_init__(self) -> None:
        require_contract(
            bool(self.detail.strip()),
            "an unavailable threshold result requires a human-readable detail",
            ContractSubject.THRESHOLD,
        )


ThresholdConstructionResult = (
    SharedThresholdResult
    | PooledSharedQuantileResult
    | SampleWeightedSharedThresholdResult
    | LocalThresholdResult
    | FamilyThresholdResult
    | GroupedThresholdResult
    | ShrinkageThresholdResult
    | ConformalThresholdResult
    | FederatedStatisticsThresholdResult
    | ThresholdUnavailableResult
)
