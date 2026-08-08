"""Family threshold construction and result contracts."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    AvailabilityStatus,
    ContractSubject,
    FederatedThresholdMethod,
)
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values.paths import FamilyIdentity
from datp_core.domain.values.ratios import Quantile, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.thresholding.assignments import (
    FamilyAssignment,
    LocalQuantile,
    ThresholdAssignment,
    mean_local_threshold,
    require_unique_clients,
    validate_assignments,
    validate_group_membership,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    local_quantile,
    require_eligible_cohort,
)


@dataclass(frozen=True, slots=True)
class FamilyMembership:
    family_id: FamilyIdentity
    members: tuple[ClientIdentity, ...]
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    status: AvailabilityStatus
    family_threshold: ThresholdValue | None

    def __post_init__(self) -> None:
        available = self.status is AvailabilityStatus.AVAILABLE
        has_support = bool(self.members) and self.family_threshold is not None
        has_leftover = bool(self.members) or self.family_threshold is not None
        require_contract(
            not available or has_support,
            "an available family requires eligible members and a constructed threshold",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            available or not has_leftover,
            "an unavailable family must carry no members and no threshold",
            ContractSubject.THRESHOLD,
        )
        if not self.members:
            require_contract(
                not self.contributing_local_quantiles,
                "an empty family membership cannot carry contributing local quantiles",
                ContractSubject.CLIENT_IDENTITY,
            )
            return
        if self.family_threshold is None:
            raise ScientificContractError(
                "non-empty family membership requires a constructed threshold",
                subject=ContractSubject.THRESHOLD,
            )
        validate_group_membership(
            self.members,
            self.contributing_local_quantiles,
            self.family_threshold,
            members_label="family members",
            match_message=("contributing local quantile clients must exactly match declared family members"),
            threshold_message=("family_threshold must equal the unweighted mean of contributing local quantiles"),
        )


@dataclass(frozen=True, slots=True)
class FamilyThresholdResult:
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
        family_ids = tuple(item.family_id for item in self.families)
        require_contract(
            len(set(family_ids)) == len(family_ids),
            "family identities must be unique",
            ContractSubject.THRESHOLD,
        )
        for family in self.families:
            for item in family.contributing_local_quantiles:
                require_contract(
                    item.coordinate == self.coordinate,
                    "every nested quantile must carry the containing result coordinate",
                    ContractSubject.COORDINATE,
                )
        expected_assignments = tuple(
            ThresholdAssignment(client, family.family_threshold)
            for family in self.families
            if family.status is AvailabilityStatus.AVAILABLE and family.family_threshold is not None
            for client in family.members
        )
        validate_assignments(
            self.assignments,
            expected_assignments,
            label="threshold assignments",
            mismatch_message=("a family threshold assignment must use its family's constructed threshold"),
        )


def construct_family_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    quantile: Quantile,
    family_by_client: tuple[FamilyAssignment, ...],
) -> FamilyThresholdResult:
    if not family_by_client:
        raise ScientificContractError(
            "family threshold construction requires a non-empty family taxonomy",
            subject=ContractSubject.THRESHOLD,
        )
    require_eligible_cohort(eligible, "family threshold construction")
    eligible_clients = tuple(item.client for item in eligible)
    require_unique_clients(
        eligible_clients,
        "eligible clients in family threshold construction",
    )
    for client in eligible_clients:
        matching = tuple(item.family for item in family_by_client if item.client == client)
        if not matching:
            raise ScientificContractError(
                f"eligible client {client} is missing a family taxonomy entry",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if len(matching) > 1:
            raise ScientificContractError(
                f"eligible client {client} has multiple family taxonomy entries",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
    family_ids = tuple(
        sorted(
            frozenset(item.family for item in family_by_client),
            key=lambda item: item.value,
        )
    )
    memberships: list[FamilyMembership] = []
    assignments: list[ThresholdAssignment] = []
    for family_id in family_ids:
        declared_members = tuple(item.client for item in family_by_client if item.family == family_id)
        membership, family_assignments = _build_family_membership(
            family_id,
            declared_members,
            eligible,
            quantile,
        )
        memberships.append(membership)
        assignments.extend(family_assignments)
    return FamilyThresholdResult(
        coordinate=eligible[0].coordinate,
        families=tuple(memberships),
        assignments=tuple(assignments),
    )


def _build_family_membership(
    family_id: FamilyIdentity,
    declared_members: tuple[ClientIdentity, ...],
    eligible: tuple[ClientBenignCalibrationScores, ...],
    quantile: Quantile,
) -> tuple[FamilyMembership, tuple[ThresholdAssignment, ...]]:
    eligible_members = tuple(client for client in declared_members if any(item.client == client for item in eligible))
    if not eligible_members:
        return (
            FamilyMembership(
                family_id=family_id,
                members=(),
                contributing_local_quantiles=(),
                status=AvailabilityStatus.UNAVAILABLE,
                family_threshold=None,
            ),
            (),
        )
    local_quantiles = tuple(local_quantile(_eligible_scores(eligible, client), quantile) for client in eligible_members)
    family_threshold = mean_local_threshold(local_quantiles)
    return (
        FamilyMembership(
            family_id=family_id,
            members=eligible_members,
            contributing_local_quantiles=local_quantiles,
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=family_threshold,
        ),
        tuple(ThresholdAssignment(client, family_threshold) for client in eligible_members),
    )


def _eligible_scores(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    client: ClientIdentity,
) -> ClientBenignCalibrationScores:
    matches = tuple(item for item in eligible if item.client == client)
    if len(matches) != 1:
        raise ScientificContractError(
            "family threshold client must resolve exactly once in eligible scores",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]
