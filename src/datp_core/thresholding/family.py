"""`FAMILY_THRESHOLD`: arithmetic mean of eligible local thresholds within each device family.

Family membership is supplied by the caller as a plain `(client, family)` mapping
rather than imported from a dataset-specific taxonomy module, so this file stays
dataset-agnostic; capability gating (only the audited N-BaIoT physical-device
population may supply a taxonomy) is enforced upstream in `thresholding.dispatch`.
There is no locked `FAMILY_THRESHOLD` protocol declaration distinct from the
canonical quantile target, so this method takes the quantile directly rather than
a `QuantileProtocol` (whose `method` field is restricted to the shared-construction
methods only).
"""

from datp_core.domain.enums import AvailabilityStatus, ContractSubject
from datp_core.domain.enums import FederatedThresholdMethod as Method
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import FamilyIdentity, Quantile, ThresholdValue
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import FamilyMembership, FamilyThresholdResult, ThresholdAssignment
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores, local_quantile, unweighted_mean


def construct_family_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    quantile: Quantile,
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...],
) -> FamilyThresholdResult:
    if not family_by_client:
        raise ScientificContractError(
            "family threshold construction requires a non-empty family taxonomy", subject=ContractSubject.THRESHOLD
        )
    if not eligible:
        raise ScientificContractError(
            "family threshold construction requires at least one eligible client", subject=ContractSubject.THRESHOLD
        )
    eligible_clients = tuple(item.client for item in eligible)
    if len(set(eligible_clients)) != len(eligible_clients):
        raise ScientificContractError(
            "eligible clients must be unique in family threshold construction",
            subject=ContractSubject.CLIENT_IDENTITY,
        )

    taxonomy_counts: dict[ClientIdentity, int] = {}
    for client, _ in family_by_client:
        taxonomy_counts[client] = taxonomy_counts.get(client, 0) + 1

    for client in eligible_clients:
        count = taxonomy_counts.get(client, 0)
        if count == 0:
            raise ScientificContractError(
                f"eligible client {client} is missing a family taxonomy entry",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if count > 1:
            raise ScientificContractError(
                f"eligible client {client} has multiple family taxonomy entries",
                subject=ContractSubject.CLIENT_IDENTITY,
            )

    eligible_by_client = {client_scores.client: client_scores for client_scores in eligible}
    coordinate = eligible[0].coordinate
    families: dict[FamilyIdentity, list[ClientIdentity]] = {}
    for client, family_id in family_by_client:
        families.setdefault(family_id, []).append(client)

    memberships: list[FamilyMembership] = []
    assignments: list[ThresholdAssignment] = []
    for family_id in sorted(families, key=lambda identity: identity.value):
        membership, family_assignments = _build_family_membership(
            family_id, tuple(families[family_id]), eligible_by_client, quantile
        )
        memberships.append(membership)
        assignments.extend(family_assignments)

    return FamilyThresholdResult(
        method=Method.FAMILY_THRESHOLD,
        coordinate=coordinate,
        families=tuple(memberships),
        assignments=tuple(assignments),
    )


def _build_family_membership(
    family_id: FamilyIdentity,
    declared_members: tuple[ClientIdentity, ...],
    eligible_by_client: dict[ClientIdentity, ClientBenignCalibrationScores],
    quantile: Quantile,
) -> tuple[FamilyMembership, tuple[ThresholdAssignment, ...]]:
    eligible_members = tuple(client for client in declared_members if client in eligible_by_client)
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
    local_quantiles = tuple(local_quantile(eligible_by_client[client], quantile) for client in eligible_members)
    family_threshold = ThresholdValue(unweighted_mean(tuple(item.value.value for item in local_quantiles)))
    membership = FamilyMembership(
        family_id=family_id,
        members=eligible_members,
        contributing_local_quantiles=local_quantiles,
        status=AvailabilityStatus.AVAILABLE,
        family_threshold=family_threshold,
    )
    assignments = tuple(ThresholdAssignment(client, family_threshold) for client in eligible_members)
    return membership, assignments
