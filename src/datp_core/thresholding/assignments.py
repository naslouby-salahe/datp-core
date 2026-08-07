"""Cross-method threshold diagnostics, local quantiles, and assignments."""

from dataclasses import dataclass
from statistics import fmean

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    AvailabilityStatus,
    ContractSubject,
    FederatedThresholdMethod,
    QuantileInterpolationSemantics,
)
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values.base import floats_absolutely_close, floats_exactly_equal
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.paths import FamilyIdentity
from datp_core.domain.values.ratios import NormalizedWeight, Quantile, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.splits import FRACTION_TOTAL_ABSOLUTE_TOLERANCE


@dataclass(frozen=True, slots=True)
class ThresholdDiagnostic:
    quantile_interpolation: QuantileInterpolationSemantics | None
    score_set_checksum: Checksum
    calibration_manifest_checksum: Checksum
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
            "a local quantile requires at least one benign calibration score",
            ContractSubject.CALIBRATION,
        )


@dataclass(frozen=True, slots=True)
class ThresholdAssignment:
    client: ClientIdentity
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True)
class FamilyAssignment:
    client: ClientIdentity
    family: FamilyIdentity


def mean_local_threshold(quantiles: tuple[LocalQuantile, ...]) -> ThresholdValue:
    return ThresholdValue(fmean(item.value.value for item in quantiles))


def median_local_threshold(quantiles: tuple[LocalQuantile, ...]) -> ThresholdValue:
    ordered = tuple(sorted(item.value.value for item in quantiles))
    count = len(ordered)
    if count == 0:
        raise ValueError("median local threshold requires at least one local quantile")
    mid = count // 2
    if count % 2 == 1:
        return ThresholdValue(ordered[mid])
    return ThresholdValue((ordered[mid - 1] + ordered[mid]) / 2.0)


def require_unique_clients(
    clients: tuple[ClientIdentity, ...],
    label: str,
) -> None:
    require_contract(
        len(set(clients)) == len(clients),
        f"{label} must have unique client identities",
        ContractSubject.CLIENT_IDENTITY,
    )


def validate_local_quantiles(
    quantiles: tuple[LocalQuantile, ...],
    coordinate: FederatedTrainingCoordinate,
    *,
    method: FederatedThresholdMethod,
) -> None:
    match method:
        case FederatedThresholdMethod.LOCAL_THRESHOLD:
            message = "local threshold construction requires at least one eligible client"
            uniqueness_label = "local quantiles"
        case FederatedThresholdMethod.SHARED_THRESHOLD | FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD:
            message = "shared threshold construction requires at least one contributing local quantile"
            uniqueness_label = "contributing local quantiles"
        case _:
            raise ScientificContractError(
                f"local quantile validation does not support threshold method {method}",
                subject=ContractSubject.THRESHOLD,
            )
    require_contract(bool(quantiles), message, ContractSubject.THRESHOLD)
    require_unique_clients(tuple(item.client for item in quantiles), uniqueness_label)
    for item in quantiles:
        require_contract(
            item.coordinate == coordinate,
            "every nested quantile must carry the containing result coordinate",
            ContractSubject.COORDINATE,
        )


def validate_assignments(
    assignments: tuple[ThresholdAssignment, ...],
    expected_assignments: tuple[ThresholdAssignment, ...],
    *,
    label: str,
    mismatch_message: str,
) -> None:
    assigned_clients = tuple(item.client for item in assignments)
    require_unique_clients(assigned_clients, label)
    expected_clients = tuple(item.client for item in expected_assignments)
    require_unique_clients(expected_clients, "expected clients")
    require_contract(
        frozenset(assigned_clients) == frozenset(expected_clients),
        "threshold assignments must cover exactly the contributing client set",
        ContractSubject.CLIENT_IDENTITY,
    )
    require_contract(
        frozenset(assignments) == frozenset(expected_assignments),
        mismatch_message,
        ContractSubject.THRESHOLD,
    )


def validate_normalized_weights(
    weights: tuple[NormalizedWeight, ...],
    quantiles: tuple[LocalQuantile, ...],
) -> None:
    require_contract(
        len(weights) == len(quantiles),
        "one normalized weight is required per contributing local quantile",
        ContractSubject.THRESHOLD,
    )
    require_contract(
        floats_absolutely_close(
            sum(weight.value for weight in weights),
            1.0,
            FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
        ),
        "normalized weights must sum to one",
        ContractSubject.THRESHOLD,
    )


def validate_group_membership(
    members: tuple[ClientIdentity, ...],
    contributing_local_quantiles: tuple[LocalQuantile, ...],
    group_threshold: ThresholdValue,
    *,
    members_label: str,
    match_message: str,
    threshold_message: str,
    expected_group_threshold: ThresholdValue | None = None,
) -> None:
    require_unique_clients(members, members_label)
    quantile_clients = tuple(item.client for item in contributing_local_quantiles)
    require_unique_clients(quantile_clients, "contributing local quantiles")
    require_contract(
        frozenset(quantile_clients) == frozenset(members),
        match_message,
        ContractSubject.CLIENT_IDENTITY,
    )
    expected = (
        expected_group_threshold
        if expected_group_threshold is not None
        else mean_local_threshold(contributing_local_quantiles)
    )
    require_contract(
        floats_exactly_equal(
            group_threshold.value,
            expected.value,
        ),
        threshold_message,
        ContractSubject.THRESHOLD,
    )


def validate_client_partition(
    eligible_clients: tuple[ClientIdentity, ...],
    assigned_clients: tuple[ClientIdentity, ...],
    unavailable_clients: tuple[ClientIdentity, ...],
) -> None:
    require_unique_clients(eligible_clients, "eligible clients")
    require_unique_clients(assigned_clients, "conformal assignments")
    require_unique_clients(unavailable_clients, "unavailable clients")
    assigned_set = frozenset(assigned_clients)
    unavailable_set = frozenset(unavailable_clients)
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
