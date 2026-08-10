"""Benign-only threshold protocols, assignments, and validation contracts."""

from dataclasses import dataclass
from enum import StrEnum
from statistics import fmean
from typing import ClassVar, Protocol, runtime_checkable

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
    require_contract,
)
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    ContractSubject,
    FederatedThresholdMethod,
    NonEmptyString,
    QuantileInterpolationSemantics,
    ValidationLabel,
)
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    NormalizedWeight,
    Quantile,
    RowCount,
    ThresholdValue,
    floats_absolutely_close,
    floats_exactly_equal,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


class ThresholdInfeasibilityReason(StrEnum):
    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = "size_aware_shrinkage_function_unresolved"
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = "group_count_exceeds_eligible_population"


@dataclass(frozen=True, slots=True)
class ThresholdUnavailableResult:
    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    reason: ThresholdInfeasibilityReason
    detail: AnalysisReasonText


@dataclass(frozen=True, slots=True)
class ThresholdDiagnostic:
    quantile_interpolation: QuantileInterpolationSemantics | None
    tie_count: RowCount
    availability: AvailabilityStatus


@dataclass(frozen=True, slots=True)
class LocalQuantile:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    value: ThresholdValue
    calibration_count: RowCount
    diagnostic: ThresholdDiagnostic

    def __post_init__(self) -> None:
        require_contract(
            self.calibration_count.value >= 1,
            ErrorMessage("a local quantile requires at least one benign calibration score"),
            ContractSubject.CALIBRATION,
        )


@dataclass(frozen=True, slots=True)
class ThresholdAssignment:
    client: ClientIdentity
    threshold: ThresholdValue


@runtime_checkable
class ThresholdAssignmentLike(Protocol):
    @property
    def client(self) -> ClientIdentity: ...

    @property
    def threshold(self) -> ThresholdValue: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdAssignmentSet[AssignmentT: ThresholdAssignmentLike]:
    assignments: tuple[AssignmentT, ...]

    def __post_init__(self) -> None:
        if not self.assignments:
            raise ScientificContractError(
                ErrorMessage("threshold assignment set requires at least one assignment"),
                subject=ContractSubject.THRESHOLD,
            )
        clients = tuple(item.client for item in self.assignments)
        if len(frozenset(clients)) != len(clients):
            raise ScientificContractError(
                ErrorMessage("threshold assignment clients must be unique"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )

    @property
    def clients(self) -> tuple[ClientIdentity, ...]:
        return tuple(item.client for item in self.assignments)


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionContext:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile


@runtime_checkable
class FederatedThresholdResult(Protocol):
    coordinate: FederatedTrainingCoordinate
    assignments: tuple[ThresholdAssignmentLike, ...]
    method: ClassVar[FederatedThresholdMethod]


def mean_local_threshold(quantiles: tuple[LocalQuantile, ...]) -> ThresholdValue:
    if not quantiles:
        raise ScientificContractError(
            ErrorMessage("mean local threshold requires local quantiles"), subject=ContractSubject.THRESHOLD
        )
    return ThresholdValue(fmean(item.value.value for item in quantiles))


def median_local_threshold(quantiles: tuple[LocalQuantile, ...]) -> ThresholdValue:
    ordered = tuple(sorted(item.value.value for item in quantiles))
    if not ordered:
        raise ScientificContractError(
            ErrorMessage("median local threshold requires local quantiles"), subject=ContractSubject.THRESHOLD
        )
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ThresholdValue(ordered[midpoint])
    return ThresholdValue((ordered[midpoint - 1] + ordered[midpoint]) / 2.0)


def require_unique_clients(clients: tuple[ClientIdentity, ...], label: NonEmptyString) -> None:
    require_contract(
        len(frozenset(clients)) == len(clients),
        ErrorMessage(f"{label} must have unique client identities"),
        ContractSubject.CLIENT_IDENTITY,
    )


def validate_local_quantiles(
    quantiles: tuple[LocalQuantile, ...],
    coordinate: FederatedTrainingCoordinate,
    *,
    method: FederatedThresholdMethod,
) -> None:
    if method is FederatedThresholdMethod.LOCAL_THRESHOLD:
        message = "local threshold construction requires at least one eligible client"
        label = NonEmptyString("local quantiles")
    elif method in {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    }:
        message = "shared threshold construction requires at least one contributing local quantile"
        label = NonEmptyString("contributing local quantiles")
    else:
        raise ScientificContractError(
            ErrorMessage(f"local quantile validation does not support threshold method {method}"),
            subject=ContractSubject.THRESHOLD,
        )
    require_contract(bool(quantiles), ErrorMessage(message), ContractSubject.THRESHOLD)
    require_unique_clients(tuple(item.client for item in quantiles), label)
    for item in quantiles:
        require_contract(
            item.coordinate == coordinate,
            ErrorMessage("every nested quantile must carry the containing result coordinate"),
            ContractSubject.COORDINATE,
        )


def validate_assignments(
    assignments: tuple[ThresholdAssignment, ...],
    expected_assignments: tuple[ThresholdAssignment, ...],
    *,
    label: ValidationLabel,
    mismatch_message: ErrorMessage,
) -> None:
    assigned_clients = tuple(item.client for item in assignments)
    expected_clients = tuple(item.client for item in expected_assignments)
    require_unique_clients(assigned_clients, label)
    require_unique_clients(expected_clients, NonEmptyString("expected clients"))
    require_contract(
        frozenset(assigned_clients) == frozenset(expected_clients),
        ErrorMessage("threshold assignments must cover exactly the contributing client set"),
        ContractSubject.CLIENT_IDENTITY,
    )
    require_contract(
        frozenset(assignments) == frozenset(expected_assignments),
        ErrorMessage(mismatch_message),
        ContractSubject.THRESHOLD,
    )


def validate_normalized_weights(
    weights: tuple[NormalizedWeight, ...],
    quantiles: tuple[LocalQuantile, ...],
) -> None:
    require_contract(
        len(weights) == len(quantiles),
        ErrorMessage("one normalized weight is required per contributing local quantile"),
        ContractSubject.THRESHOLD,
    )
    require_contract(
        floats_absolutely_close(
            sum(weight.value for weight in weights),
            1.0,
            NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value,
        ),
        ErrorMessage("normalized weights must sum to one"),
        ContractSubject.THRESHOLD,
    )


def validate_group_membership(
    members: tuple[ClientIdentity, ...],
    contributing_local_quantiles: tuple[LocalQuantile, ...],
    group_threshold: ThresholdValue,
    *,
    members_label: ValidationLabel,
    match_message: ErrorMessage,
    threshold_message: ErrorMessage,
    expected_group_threshold: ThresholdValue | None = None,
) -> None:
    require_unique_clients(members, members_label)
    quantile_clients = tuple(item.client for item in contributing_local_quantiles)
    require_unique_clients(quantile_clients, NonEmptyString("contributing local quantiles"))
    require_contract(
        frozenset(quantile_clients) == frozenset(members),
        ErrorMessage(match_message),
        ContractSubject.CLIENT_IDENTITY,
    )
    expected = expected_group_threshold or mean_local_threshold(contributing_local_quantiles)
    require_contract(
        floats_exactly_equal(group_threshold.value, expected.value),
        ErrorMessage(threshold_message),
        ContractSubject.THRESHOLD,
    )


def validate_client_partition(
    eligible_clients: tuple[ClientIdentity, ...],
    assigned_clients: tuple[ClientIdentity, ...],
    unavailable_clients: tuple[ClientIdentity, ...],
) -> None:
    require_unique_clients(eligible_clients, NonEmptyString("eligible clients"))
    require_unique_clients(assigned_clients, NonEmptyString("assigned clients"))
    require_unique_clients(unavailable_clients, NonEmptyString("unavailable clients"))
    assigned_set = frozenset(assigned_clients)
    unavailable_set = frozenset(unavailable_clients)
    require_contract(
        not assigned_set.intersection(unavailable_set),
        ErrorMessage("a client cannot be both assigned and unavailable"),
        ContractSubject.CLIENT_IDENTITY,
    )
    require_contract(
        assigned_set.union(unavailable_set) == frozenset(eligible_clients),
        ErrorMessage("assigned and unavailable clients must exactly cover the eligible client set"),
        ContractSubject.CLIENT_IDENTITY,
    )
