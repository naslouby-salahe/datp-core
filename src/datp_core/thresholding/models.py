"""Typed, discriminated federated threshold-construction results."""

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from datp_core.domain.enums import (
    AvailabilityStatus,
    ContractSubject,
    FederatedThresholdMethod,
    KMeansInitialization,
    QuantileInterpolationSemantics,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    ByteCount,
    Checksum,
    ClusterIndex,
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

_UNIT_TOTAL_ABSOLUTE_TOLERANCE = 1e-9


def _raise_first_violation(*, requirements: tuple[tuple[bool, str], ...], subject: ContractSubject) -> None:
    for satisfied, message in requirements:
        if not satisfied:
            raise ScientificContractError(message, subject=subject)


class ThresholdInfeasibilityReason(StrEnum):
    """Closed reasons a requested federated threshold method cannot be executed."""

    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = "size_aware_shrinkage_function_unresolved"
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = "group_count_exceeds_eligible_population"


def _require_method(actual: FederatedThresholdMethod, expected: FederatedThresholdMethod) -> None:
    if actual is not expected:
        raise ScientificContractError(f"threshold result method must be {expected.value}", subject=actual)


def _require_unique_clients(clients: tuple[ClientIdentity, ...], label: str) -> None:
    if len(set(clients)) != len(clients):
        raise ScientificContractError(
            f"{label} must have unique client identities", subject=ContractSubject.CLIENT_IDENTITY
        )


def _require_uniform_shared_threshold(
    assignments: tuple["ThresholdAssignment", ...], shared_threshold: ThresholdValue
) -> None:
    if not assignments:
        raise ScientificContractError(
            "a shared threshold result requires at least one client assignment",
            subject=ContractSubject.THRESHOLD,
        )
    if any(not floats_exactly_equal(assignment.threshold.value, shared_threshold.value) for assignment in assignments):
        raise ScientificContractError(
            "every assignment in a shared threshold result must carry the identical shared value",
            subject=ContractSubject.THRESHOLD,
        )


def _require_valid_attainment_diagnostic(
    target_exceedance: float,
    achieved_exceedance: float,
    signed_attainment_error: float,
    absolute_attainment_error: float,
    absolute_threshold_error_vs_pooled_quantile: float,
    relative_threshold_error_vs_pooled_quantile: float | None,
) -> None:
    numeric_fields_finite = (
        np.isfinite(target_exceedance)
        and np.isfinite(achieved_exceedance)
        and np.isfinite(signed_attainment_error)
        and np.isfinite(absolute_attainment_error)
        and np.isfinite(absolute_threshold_error_vs_pooled_quantile)
        and (
            relative_threshold_error_vs_pooled_quantile is None
            or np.isfinite(relative_threshold_error_vs_pooled_quantile)
        )
    )
    _raise_first_violation(
        requirements=(
            (numeric_fields_finite, "every numeric field in attainment diagnostic must be finite"),
            (0 < target_exceedance < 1, "target exceedance must be in (0, 1)"),
            (0 <= achieved_exceedance <= 1, "achieved exceedance must be in [0, 1]"),
            (
                floats_exactly_equal(signed_attainment_error, achieved_exceedance - target_exceedance),
                "signed attainment error must equal achieved_exceedance - target_exceedance",
            ),
            (
                floats_exactly_equal(absolute_attainment_error, abs(signed_attainment_error)),
                "absolute attainment error must equal abs(signed_attainment_error)",
            ),
            (absolute_attainment_error >= 0, "absolute attainment error must be non-negative"),
            (
                absolute_threshold_error_vs_pooled_quantile >= 0,
                "absolute threshold error must be non-negative",
            ),
            (
                relative_threshold_error_vs_pooled_quantile is None
                or relative_threshold_error_vs_pooled_quantile >= 0,
                "relative threshold error must be non-negative when present",
            ),
        ),
        subject=ContractSubject.THRESHOLD,
    )


def _require_valid_variance_decomposition(
    within_client_variance: float,
    between_client_variance: float,
    full_pooled_variance: float,
    between_ratio: float | None,
) -> None:
    _raise_first_violation(
        requirements=(
            (within_client_variance >= 0, "within-client variance must be non-negative"),
            (between_client_variance >= 0, "between-client variance must be non-negative"),
            (
                floats_exactly_equal(full_pooled_variance, within_client_variance + between_client_variance),
                "the full pooled variance must equal within-client plus between-client variance",
            ),
            (
                between_ratio is None or 0 <= between_ratio <= 1,
                "the between-client ratio must be in [0, 1] when defined",
            ),
        ),
        subject=ContractSubject.THRESHOLD,
    )


def _require_valid_conformal_assignment(
    rank_index: int, calibration_count: RowCount, effective_quantile: float, tie_count: int
) -> None:
    _raise_first_violation(
        requirements=(
            (
                1 <= rank_index <= calibration_count.value,
                "conformal rank index must fall within the calibration sample",
            ),
            (0 < effective_quantile <= 1, "conformal effective quantile must be in (0, 1]"),
            (tie_count >= 0, "tie count must be non-negative"),
        ),
        subject=ContractSubject.THRESHOLD,
    )


def _require_disjoint_cluster_membership(
    clusters: tuple["ClusterMembership", ...],
    fingerprints: tuple["ClusterFingerprint", ...],
) -> tuple[ClientIdentity, ...]:
    all_members = tuple(client for cluster in clusters for client in cluster.members)
    if len(set(all_members)) != len(all_members):
        raise ScientificContractError(
            "a client cannot belong to more than one cluster", subject=ContractSubject.CLIENT_IDENTITY
        )
    if frozenset(all_members) != frozenset(fingerprint.client for fingerprint in fingerprints):
        raise ScientificContractError(
            "cluster membership must cover exactly the fingerprinted client set",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return all_members


def _require_family_availability_consistency(
    status: AvailabilityStatus,
    members: tuple[ClientIdentity, ...],
    family_threshold: ThresholdValue | None,
) -> None:
    is_available = status is AvailabilityStatus.AVAILABLE
    has_support = bool(members) and family_threshold is not None
    has_leftover_support = bool(members) or family_threshold is not None
    _raise_first_violation(
        requirements=(
            (
                not is_available or has_support,
                "an available family requires eligible members and a constructed threshold",
            ),
            (
                is_available or not has_leftover_support,
                "an unavailable family must carry no members and no threshold",
            ),
        ),
        subject=ContractSubject.THRESHOLD,
    )


def _require_normalized_weights(weights: tuple[float, ...], expected_count: int) -> None:
    if len(weights) != expected_count:
        raise ScientificContractError(
            "one normalized weight is required per contributing local quantile",
            subject=ContractSubject.THRESHOLD,
        )
    if any(weight < 0 for weight in weights):
        raise ScientificContractError("normalized weights must be non-negative", subject=ContractSubject.THRESHOLD)
    if not floats_absolutely_close(sum(weights), 1.0, _UNIT_TOTAL_ABSOLUTE_TOLERANCE):
        raise ScientificContractError("normalized weights must sum to one", subject=ContractSubject.THRESHOLD)


def _require_matching_clients(
    assignments: tuple["ThresholdAssignment", ...], clients: tuple[ClientIdentity, ...]
) -> None:
    assigned_ids = tuple(assignment.client for assignment in assignments)
    _require_unique_clients(assigned_ids, "threshold assignments")
    _require_unique_clients(clients, "expected clients")
    if frozenset(assigned_ids) != frozenset(clients):
        raise ScientificContractError(
            "threshold assignments must cover exactly the contributing client set",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


def _require_nested_local_quantile_coordinates(
    container_coordinate: FederatedTrainingCoordinate,
    items: tuple["LocalQuantile", ...],
) -> None:
    for item in items:
        if item.coordinate != container_coordinate:
            raise ScientificContractError(
                "every nested quantile must carry the containing result coordinate",
                subject=ContractSubject.COORDINATE,
            )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThresholdDiagnostic:
    """Shared provenance and boundary-condition record attached to a quantile computation."""

    quantile_interpolation: QuantileInterpolationSemantics | None
    score_set_checksum: Checksum
    calibration_manifest_checksum: Checksum
    tie_count: int
    availability: AvailabilityStatus

    def __post_init__(self) -> None:
        if self.tie_count < 0:
            raise ScientificContractError("tie count must be non-negative", subject=ContractSubject.THRESHOLD)


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
        if self.calibration_count < 1:
            raise ScientificContractError(
                "a local quantile requires at least one benign calibration score",
                subject=ContractSubject.CALIBRATION,
            )


@dataclass(frozen=True, slots=True)
class ThresholdAssignment:
    """One client's assigned operating threshold."""

    client: ClientIdentity
    threshold: ThresholdValue


# ---------------------------------------------------------------------------
# Shared-threshold family
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SharedThresholdResult:
    """`SHARED_THRESHOLD`: the unweighted mean of eligible local quantiles."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.SHARED_THRESHOLD)
        if not self.contributing_local_quantiles:
            raise ScientificContractError(
                "shared threshold construction requires at least one contributing local quantile",
                subject=ContractSubject.THRESHOLD,
            )
        _require_unique_clients(
            tuple(item.client for item in self.contributing_local_quantiles), "contributing local quantiles"
        )
        _require_matching_clients(self.assignments, tuple(item.client for item in self.contributing_local_quantiles))
        _require_uniform_shared_threshold(self.assignments, self.shared_threshold)
        _require_nested_local_quantile_coordinates(self.coordinate, self.contributing_local_quantiles)
        expected_shared = sum(item.value.value for item in self.contributing_local_quantiles) / len(
            self.contributing_local_quantiles
        )
        if not floats_exactly_equal(self.shared_threshold.value, expected_shared):
            raise ScientificContractError(
                "shared_threshold must equal the unweighted mean of contributing local quantiles",
                subject=ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class PooledSharedQuantileResult:
    """`POOLED_SHARED_QUANTILE`: the exact pooled benign quantile, as a centralized pooled-raw-score oracle/control."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    pooled_benign_score_count: RowCount
    diagnostic: ThresholdDiagnostic
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.POOLED_SHARED_QUANTILE)
        if self.pooled_benign_score_count < 1:
            raise ScientificContractError(
                "pooled shared quantile requires at least one pooled benign score",
                subject=ContractSubject.CALIBRATION,
            )
        _require_unique_clients(
            tuple(assignment.client for assignment in self.assignments), "pooled shared quantile assignments"
        )
        _require_uniform_shared_threshold(self.assignments, self.shared_threshold)


@dataclass(frozen=True, slots=True)
class SampleWeightedSharedThresholdResult:
    """`SAMPLE_WEIGHTED_SHARED_THRESHOLD`: local quantiles weighted by benign calibration support."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    normalized_weights: tuple[float, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD)
        _require_normalized_weights(self.normalized_weights, len(self.contributing_local_quantiles))
        _require_unique_clients(
            tuple(item.client for item in self.contributing_local_quantiles), "contributing local quantiles"
        )
        _require_matching_clients(self.assignments, tuple(item.client for item in self.contributing_local_quantiles))
        _require_uniform_shared_threshold(self.assignments, self.shared_threshold)
        _require_nested_local_quantile_coordinates(self.coordinate, self.contributing_local_quantiles)
        expected_shared = sum(
            item.value.value * weight
            for item, weight in zip(self.contributing_local_quantiles, self.normalized_weights, strict=True)
        )
        if not floats_exactly_equal(self.shared_threshold.value, expected_shared):
            raise ScientificContractError(
                "shared_threshold must equal the declared normalized weighted mean of contributing local quantiles",
                subject=ContractSubject.THRESHOLD,
            )


# ---------------------------------------------------------------------------
# Local
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LocalThresholdResult:
    """`LOCAL_THRESHOLD`: each eligible client keeps its own benign calibration quantile."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    local_quantiles: tuple[LocalQuantile, ...]
    assignments: tuple[ThresholdAssignment, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.LOCAL_THRESHOLD)
        if not self.local_quantiles:
            raise ScientificContractError(
                "local threshold construction requires at least one eligible client",
                subject=ContractSubject.THRESHOLD,
            )
        _require_unique_clients(
            tuple(item.client for item in self.local_quantiles), "local quantiles"
        )
        _require_matching_clients(self.assignments, tuple(item.client for item in self.local_quantiles))
        _require_nested_local_quantile_coordinates(self.coordinate, self.local_quantiles)
        by_client = {item.client: item.value for item in self.local_quantiles}
        for assignment in self.assignments:
            if not floats_exactly_equal(assignment.threshold.value, by_client[assignment.client].value):
                raise ScientificContractError(
                    "a local threshold assignment must equal the client's own local quantile",
                    subject=ContractSubject.THRESHOLD,
                )


# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FamilyMembership:
    """One device-family group's threshold construction outcome."""

    family_id: FamilyIdentity
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    status: AvailabilityStatus
    family_threshold: ThresholdValue | None

    def __post_init__(self) -> None:
        _require_family_availability_consistency(self.status, self.members, self.family_threshold)
        _require_unique_clients(self.members, "family members")
        quantile_clients = tuple(item.client for item in self.contributing_local_quantiles)
        _require_unique_clients(quantile_clients, "contributing local quantiles")
        if set(quantile_clients) != set(self.members):
            raise ScientificContractError(
                "contributing local quantile clients must exactly match declared family members",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if self.status is AvailabilityStatus.AVAILABLE and self.family_threshold is not None:
            expected_family = sum(item.value.value for item in self.contributing_local_quantiles) / len(
                self.contributing_local_quantiles
            )
            if not floats_exactly_equal(self.family_threshold.value, expected_family):
                raise ScientificContractError(
                    "family_threshold must equal the unweighted mean of contributing local quantiles",
                    subject=ContractSubject.THRESHOLD,
                )


@dataclass(frozen=True, slots=True)
class FamilyThresholdResult:
    """`FAMILY_THRESHOLD`: mean of eligible local thresholds within each device family."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    families: tuple[FamilyMembership, ...]
    assignments: tuple[ThresholdAssignment, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.FAMILY_THRESHOLD)
        if not self.families:
            raise ScientificContractError(
                "family threshold construction requires at least one declared family",
                subject=ContractSubject.THRESHOLD,
            )
        family_ids = tuple(family.family_id for family in self.families)
        if len(set(family_ids)) != len(family_ids):
            raise ScientificContractError("family identities must be unique", subject=ContractSubject.THRESHOLD)
        for family in self.families:
            _require_nested_local_quantile_coordinates(self.coordinate, family.contributing_local_quantiles)
        available_members = tuple(
            client
            for family in self.families
            if family.status is AvailabilityStatus.AVAILABLE
            for client in family.members
        )
        _require_matching_clients(self.assignments, available_members)
        family_threshold_by_client: dict[ClientIdentity, ThresholdValue] = {}
        for family in self.families:
            if family.status is AvailabilityStatus.AVAILABLE and family.family_threshold is not None:
                for client in family.members:
                    family_threshold_by_client[client] = family.family_threshold
        for assignment in self.assignments:
            expected = family_threshold_by_client.get(assignment.client)
            if expected is None:
                raise ScientificContractError(
                    "each assigned client must belong to an available family", subject=ContractSubject.THRESHOLD
                )
            if not floats_exactly_equal(assignment.threshold.value, expected.value):
                raise ScientificContractError(
                    "a family threshold assignment must use its family's constructed threshold",
                    subject=ContractSubject.THRESHOLD,
                )


# ---------------------------------------------------------------------------
# Cluster / Grouped
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClusterFingerprint:
    """Locked four-feature benign reconstruction-error fingerprint for one client."""

    client: ClientIdentity
    raw: tuple[float, float, float, float]
    standardized: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if len(self.raw) != 4 or len(self.standardized) != 4:
            raise ScientificContractError(
                "a cluster fingerprint must carry exactly mean, standard deviation, skewness, and p95",
                subject=ContractSubject.THRESHOLD,
            )
        if not all(np.isfinite(value) for value in self.raw):
            raise ScientificContractError(
                "every raw fingerprint feature must be finite", subject=ContractSubject.THRESHOLD
            )
        if not all(np.isfinite(value) for value in self.standardized):
            raise ScientificContractError(
                "every standardized fingerprint feature must be finite", subject=ContractSubject.THRESHOLD
            )


@dataclass(frozen=True, slots=True)
class ClusterMembership:
    """One k-means cluster's member set and aggregated threshold."""

    cluster_index: ClusterIndex
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    cluster_threshold: ThresholdValue

    def __post_init__(self) -> None:
        if not self.members:
            raise ScientificContractError(
                "a cluster membership requires at least one member", subject=ContractSubject.THRESHOLD
            )
        _require_unique_clients(self.members, "cluster members")
        quantile_clients = tuple(item.client for item in self.contributing_local_quantiles)
        _require_unique_clients(quantile_clients, "contributing local quantiles")
        if set(quantile_clients) != set(self.members):
            raise ScientificContractError(
                "contributing local quantile clients must exactly equal cluster members",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        expected_cluster = sum(item.value.value for item in self.contributing_local_quantiles) / len(
            self.contributing_local_quantiles
        )
        if not floats_exactly_equal(self.cluster_threshold.value, expected_cluster):
            raise ScientificContractError(
                "cluster_threshold must equal the unweighted mean of contributing local quantiles",
                subject=ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class GroupedThresholdResult:
    """`CLUSTER_THRESHOLD`: locked benign-error fingerprint k-means grouping."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    fingerprints: tuple[ClusterFingerprint, ...]
    clusters: tuple[ClusterMembership, ...]
    assignments: tuple[ThresholdAssignment, ...]
    initialization: KMeansInitialization
    initialization_count: KMeansInitializationCount
    maximum_iterations: KMeansMaximumIterationCount
    random_state: Seed
    group_count: GroupCount

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.CLUSTER_THRESHOLD)
        if len(self.clusters) != self.group_count.value:
            raise ScientificContractError(
                "the number of clusters must equal the declared group count",
                subject=ContractSubject.THRESHOLD,
            )
        fingerprint_clients = tuple(fp.client for fp in self.fingerprints)
        _require_unique_clients(fingerprint_clients, "fingerprint")
        cluster_indices = tuple(cluster.cluster_index.value for cluster in self.clusters)
        expected_indices = set(range(self.group_count.value))
        if set(cluster_indices) != expected_indices or len(cluster_indices) != len(expected_indices):
            raise ScientificContractError(
                "cluster indices must equal exactly 0..group_count.value - 1", subject=ContractSubject.THRESHOLD
            )
        for cluster in self.clusters:
            _require_nested_local_quantile_coordinates(self.coordinate, cluster.contributing_local_quantiles)
        all_members = _require_disjoint_cluster_membership(self.clusters, self.fingerprints)
        _require_matching_clients(self.assignments, all_members)
        cluster_threshold_by_client: dict[ClientIdentity, ThresholdValue] = {}
        for cluster in self.clusters:
            for client in cluster.members:
                cluster_threshold_by_client[client] = cluster.cluster_threshold
        for assignment in self.assignments:
            expected = cluster_threshold_by_client.get(assignment.client)
            if expected is None:
                raise ScientificContractError(
                    "each assigned client must belong to a cluster", subject=ContractSubject.THRESHOLD
                )
            if not floats_exactly_equal(assignment.threshold.value, expected.value):
                raise ScientificContractError(
                    "a cluster threshold assignment must use its cluster's threshold",
                    subject=ContractSubject.THRESHOLD,
                )


# ---------------------------------------------------------------------------
# Shrinkage
# ---------------------------------------------------------------------------


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
        if not floats_exactly_equal(self.blended_threshold.value, expected):
            raise ScientificContractError(
                "blended threshold must equal lambda * local + (1 - lambda) * shared",
                subject=ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class ShrinkageThresholdResult:
    """`LOCAL_GLOBAL_SHRINKAGE`: the complete fixed lambda-curve of blended thresholds."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    weights: tuple[ShrinkageWeight, ...]
    assignments: tuple[ShrinkageAssignment, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE)
        if not self.weights:
            raise ScientificContractError(
                "shrinkage construction requires at least one declared lambda", subject=ContractSubject.THRESHOLD
            )
        if len(set(self.weights)) != len(self.weights):
            raise ScientificContractError(
                "declared shrinkage weights must be unique", subject=ContractSubject.THRESHOLD
            )
        if not self.assignments:
            raise ScientificContractError(
                "shrinkage construction requires at least one client assignment",
                subject=ContractSubject.THRESHOLD,
            )
        declared_weight_set = frozenset(self.weights)
        assignments_by_key: dict[tuple[ClientIdentity, ShrinkageWeight], int] = {}
        for assignment in self.assignments:
            if assignment.lambda_weight not in declared_weight_set:
                raise ScientificContractError(
                    "every shrinkage assignment must use a declared lambda weight",
                    subject=ContractSubject.THRESHOLD,
                )
            key = (assignment.client, assignment.lambda_weight)
            if key in assignments_by_key:
                raise ScientificContractError(
                    "exactly one shrinkage assignment is required per (client, lambda_weight) pair",
                    subject=ContractSubject.THRESHOLD,
                )
            assignments_by_key[key] = 1
        clients = frozenset(assignment.client for assignment in self.assignments)
        for weight in self.weights:
            observed = frozenset(
                assignment.client for assignment in self.assignments if assignment.lambda_weight == weight
            )
            if observed != clients:
                raise ScientificContractError(
                    "every declared lambda must be evaluated for exactly the same client set",
                    subject=ContractSubject.THRESHOLD,
                )
        expected_combinations = len(clients) * len(self.weights)
        if len(self.assignments) != expected_combinations:
            raise ScientificContractError(
                "every declared (client, lambda_weight) combination must exist exactly once",
                subject=ContractSubject.THRESHOLD,
            )


# ---------------------------------------------------------------------------
# Conformal
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConformalAssignment:
    """One client's finite-sample local conformal threshold."""

    client: ClientIdentity
    calibration_count: RowCount
    rank_index: int
    effective_quantile: float
    selected_score: ScoreValue
    tie_count: int
    threshold: ThresholdValue

    def __post_init__(self) -> None:
        _require_valid_conformal_assignment(
            self.rank_index, self.calibration_count, self.effective_quantile, self.tie_count
        )
        if not floats_exactly_equal(self.threshold.value, self.selected_score.value):
            raise ScientificContractError(
                "conformal threshold value must equal the selected score", subject=ContractSubject.THRESHOLD
            )
        if not np.isfinite(self.effective_quantile):
            raise ScientificContractError(
                "conformal effective quantile must be finite", subject=ContractSubject.THRESHOLD
            )
        if not np.isfinite(self.selected_score.value):
            raise ScientificContractError(
                "conformal selected score must be finite", subject=ContractSubject.THRESHOLD
            )
        expected_quantile = self.rank_index / self.calibration_count.value
        if not floats_absolutely_close(self.effective_quantile, expected_quantile, _UNIT_TOTAL_ABSOLUTE_TOLERANCE):
            raise ScientificContractError(
                "conformal effective quantile must equal rank_index / calibration_count",
                subject=ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class ConformalThresholdResult:
    """`LOCAL_CONFORMAL_THRESHOLD`: finite-sample local conformal thresholds."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    coverage: CoverageTarget
    significance: Ratio
    eligible_clients: tuple[ClientIdentity, ...]
    assignments: tuple[ConformalAssignment, ...]
    unavailable_clients: tuple[ClientIdentity, ...]

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD)
        if not floats_absolutely_close(
            self.coverage.value + self.significance.value, 1.0, _UNIT_TOTAL_ABSOLUTE_TOLERANCE
        ):
            raise ScientificContractError(
                "conformal coverage and significance must be complements", subject=ContractSubject.THRESHOLD
            )
        _require_unique_clients(self.eligible_clients, "eligible clients")
        if not self.assignments:
            raise ScientificContractError(
                "a conformal threshold result requires at least one assigned client",
                subject=ContractSubject.THRESHOLD,
            )
        assigned_clients = tuple(assignment.client for assignment in self.assignments)
        _require_unique_clients(assigned_clients, "conformal assignments")
        _require_unique_clients(self.unavailable_clients, "unavailable clients")
        assigned_set = frozenset(assigned_clients)
        unavailable_set = frozenset(self.unavailable_clients)
        if assigned_set & unavailable_set:
            raise ScientificContractError(
                "a client cannot be both assigned and unavailable", subject=ContractSubject.CLIENT_IDENTITY
            )
        if assigned_set | unavailable_set != frozenset(self.eligible_clients):
            raise ScientificContractError(
                "assigned and unavailable clients must exactly cover the eligible client set",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


# ---------------------------------------------------------------------------
# Federated benign statistics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClientBenignSummary:
    """Benign-only summary statistics one client may communicate: count, mean, variance."""

    client: ClientIdentity
    count: RowCount
    mean: float
    variance: float
    benign_exceedance_count: int | None

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ScientificContractError(
                "a benign summary requires at least one calibration score", subject=ContractSubject.CALIBRATION
            )
        if self.variance < 0:
            raise ScientificContractError("variance must be non-negative", subject=ContractSubject.THRESHOLD)
        if self.benign_exceedance_count is not None and self.benign_exceedance_count < 0:
            raise ScientificContractError(
                "benign exceedance count must be non-negative", subject=ContractSubject.THRESHOLD
            )
        if not np.isfinite(self.mean):
            raise ScientificContractError("summary mean must be finite", subject=ContractSubject.THRESHOLD)
        if not np.isfinite(self.variance):
            raise ScientificContractError("summary variance must be finite", subject=ContractSubject.THRESHOLD)


@dataclass(frozen=True, slots=True)
class PooledVarianceDecomposition:
    """Between/within decomposition of the pooled benign score variance."""

    global_mean: float
    within_client_variance: float
    between_client_variance: float
    full_pooled_variance: float
    between_ratio: float | None

    def __post_init__(self) -> None:
        _require_valid_variance_decomposition(
            self.within_client_variance, self.between_client_variance, self.full_pooled_variance, self.between_ratio
        )
        if not np.isfinite(self.global_mean):
            raise ScientificContractError("decomposition global mean must be finite", subject=ContractSubject.THRESHOLD)
        if not np.isfinite(self.full_pooled_variance):
            raise ScientificContractError(
                "decomposition full pooled variance must be finite", subject=ContractSubject.THRESHOLD
            )


@dataclass(frozen=True, slots=True)
class CentralizedAttainmentDiagnostic:
    """Centralized oracle attainment diagnostic computed from full pooled raw scores.

    All fields depend on access to the complete pooled raw scores, which are never
    communicated in the federated protocol.  This record is a centralized diagnostic,
    not a federated input.
    """

    target_exceedance: float
    achieved_exceedance: float
    signed_attainment_error: float
    absolute_attainment_error: float
    absolute_threshold_error_vs_pooled_quantile: float
    relative_threshold_error_vs_pooled_quantile: float | None

    def __post_init__(self) -> None:
        _require_valid_attainment_diagnostic(
            self.target_exceedance,
            self.achieved_exceedance,
            self.signed_attainment_error,
            self.absolute_attainment_error,
            self.absolute_threshold_error_vs_pooled_quantile,
            self.relative_threshold_error_vs_pooled_quantile,
        )


@dataclass(frozen=True, slots=True)
class FixedCoefficientResult:
    """One supplementary sensitivity point on the fixed-coefficient curve."""

    coefficient: SummaryCoefficient
    threshold: ThresholdValue

    def __post_init__(self) -> None:
        if not np.isfinite(self.threshold.value):
            raise ScientificContractError(
                "fixed-coefficient threshold must be finite", subject=ContractSubject.THRESHOLD
            )


@dataclass(frozen=True, slots=True)
class CommunicationPayload:
    """Estimated (not measured) serialized byte size of one round of communicated fields."""

    fields: tuple[str, ...]
    estimated_bytes: ByteCount

    def __post_init__(self) -> None:
        if not self.fields:
            raise ScientificContractError(
                "a communication payload must declare at least one communicated field",
                subject=ContractSubject.THRESHOLD,
            )
        if len(set(self.fields)) != len(self.fields):
            raise ScientificContractError(
                "communication payload fields must be unique", subject=ContractSubject.THRESHOLD
            )


@dataclass(frozen=True, slots=True)
class FederatedStatisticsThresholdResult:
    """`FEDERATED_BENIGN_STATISTICS`: federated benign summary-statistics comparator.

    Only count, mean, and variance are federated inputs.  The matched-exceedance
    threshold is constructed from those summaries under a Gaussian-tail assumption.
    ``centralized_pooled_quantile_diagnostic`` and ``centralized_attainment_diagnostic``
    are centralized oracle diagnostics computed from the full pooled raw scores —
    they are never federated comparators and raw pooled scores are never communicated.
    """

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    client_summaries: tuple[ClientBenignSummary, ...]
    decomposition: PooledVarianceDecomposition
    matched_threshold: ThresholdValue
    centralized_attainment_diagnostic: CentralizedAttainmentDiagnostic
    centralized_pooled_quantile_diagnostic: ThresholdValue
    fixed_coefficient_curve: tuple[FixedCoefficientResult, ...]
    assignments: tuple[ThresholdAssignment, ...]
    communication_payload: CommunicationPayload

    def __post_init__(self) -> None:
        _require_method(self.method, FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS)
        if not self.client_summaries:
            raise ScientificContractError(
                "the federated benign-statistics comparator requires at least one client summary",
                subject=ContractSubject.THRESHOLD,
            )
        summary_clients = tuple(summary.client for summary in self.client_summaries)
        _require_unique_clients(summary_clients, "client summaries")
        _require_matching_clients(self.assignments, summary_clients)
        _require_uniform_shared_threshold(self.assignments, self.matched_threshold)
        if not np.isfinite(self.matched_threshold.value):
            raise ScientificContractError("matched threshold must be finite", subject=ContractSubject.THRESHOLD)
        if set(self.communication_payload.fields) != {"count", "mean", "variance"}:
            raise ScientificContractError(
                "communication payload fields must be exactly count, mean, and variance",
                subject=ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class ThresholdUnavailableResult:
    """A requested federated threshold method that cannot be executed, with a typed reason."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    reason: ThresholdInfeasibilityReason
    detail: str

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise ScientificContractError(
                "an unavailable threshold result requires a human-readable detail", subject=ContractSubject.THRESHOLD
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
