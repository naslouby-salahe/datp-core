"""Typed, discriminated federated threshold-construction results."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.calibration.models import _raise_first_violation
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


class ThresholdInfeasibilityReason(StrEnum):
    """Closed reasons a requested federated threshold method cannot be executed."""

    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = "size_aware_shrinkage_function_unresolved"
    INSUFFICIENT_ELIGIBLE_SUPPORT = "insufficient_eligible_support"
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = "group_count_exceeds_eligible_population"
    CENTRALIZED_METHOD_REJECTED = "centralized_method_rejected"


def _require_method(actual: FederatedThresholdMethod, expected: FederatedThresholdMethod) -> None:
    if actual is not expected:
        raise ScientificContractError(f"threshold result method must be {expected.value}", subject=actual)


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
    absolute_attainment_error: float,
    absolute_threshold_error_vs_pooled_quantile: float,
) -> None:
    _raise_first_violation(
        requirements=(
            (0 < target_exceedance < 1, "target exceedance must be in (0, 1)"),
            (0 <= achieved_exceedance <= 1, "achieved exceedance must be in [0, 1]"),
            (absolute_attainment_error >= 0, "absolute attainment error must be non-negative"),
            (
                absolute_threshold_error_vs_pooled_quantile >= 0,
                "absolute threshold error must be non-negative",
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
    assigned = frozenset(assignment.client for assignment in assignments)
    expected = frozenset(clients)
    if assigned != expected:
        raise ScientificContractError(
            "threshold assignments must cover exactly the contributing client set",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


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
        _require_matching_clients(self.assignments, tuple(item.client for item in self.contributing_local_quantiles))
        _require_uniform_shared_threshold(self.assignments, self.shared_threshold)


@dataclass(frozen=True, slots=True)
class PooledSharedQuantileResult:
    """`POOLED_SHARED_QUANTILE`: the exact pooled benign quantile, as a federated control."""

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
        _require_matching_clients(self.assignments, tuple(item.client for item in self.contributing_local_quantiles))
        _require_uniform_shared_threshold(self.assignments, self.shared_threshold)


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
        _require_matching_clients(self.assignments, tuple(item.client for item in self.local_quantiles))
        by_client = {item.client: item.value for item in self.local_quantiles}
        for assignment in self.assignments:
            if not floats_exactly_equal(assignment.threshold.value, by_client[assignment.client].value):
                raise ScientificContractError(
                    "a local threshold assignment must equal the client's own local quantile",
                    subject=ContractSubject.THRESHOLD,
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
        _require_family_availability_consistency(self.status, self.members, self.family_threshold)


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
        available_members = tuple(
            client
            for family in self.families
            if family.status is AvailabilityStatus.AVAILABLE
            for client in family.members
        )
        _require_matching_clients(self.assignments, available_members)


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
        all_members = _require_disjoint_cluster_membership(self.clusters, self.fingerprints)
        _require_matching_clients(self.assignments, all_members)


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


@dataclass(frozen=True, slots=True)
class ConformalThresholdResult:
    """`LOCAL_CONFORMAL_THRESHOLD`: finite-sample local conformal thresholds."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    coverage: CoverageTarget
    significance: Ratio
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
        assigned = frozenset(assignment.client for assignment in self.assignments)
        if assigned & frozenset(self.unavailable_clients):
            raise ScientificContractError(
                "a client cannot be both assigned and unavailable", subject=ContractSubject.CLIENT_IDENTITY
            )


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


@dataclass(frozen=True, slots=True)
class MatchedAttainmentDiagnostic:
    """Attainment and threshold-error diagnostics for the matched-exceedance comparator."""

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
            self.absolute_attainment_error,
            self.absolute_threshold_error_vs_pooled_quantile,
        )


@dataclass(frozen=True, slots=True)
class FixedCoefficientResult:
    """One supplementary sensitivity point on the fixed-coefficient curve."""

    coefficient: SummaryCoefficient
    threshold: ThresholdValue


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


@dataclass(frozen=True, slots=True)
class FederatedStatisticsThresholdResult:
    """`FEDERATED_BENIGN_STATISTICS`: benign summary-statistics comparator with mandatory between-client term."""

    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    client_summaries: tuple[ClientBenignSummary, ...]
    decomposition: PooledVarianceDecomposition
    matched_threshold: ThresholdValue
    matched_diagnostic: MatchedAttainmentDiagnostic
    exact_pooled_quantile_reference: ThresholdValue
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
        _require_uniform_shared_threshold(self.assignments, self.matched_threshold)


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
