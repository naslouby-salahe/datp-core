"""Shared threshold-result structure without collapsing method-specific science."""

from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Quantile, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


@runtime_checkable
class ThresholdAssignmentLike(Protocol):
    client: ClientIdentity
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdAssignmentSet[AssignmentT: ThresholdAssignmentLike]:
    assignments: tuple[AssignmentT, ...]

    def __post_init__(self) -> None:
        if not self.assignments:
            raise ScientificContractError(
                "threshold assignment set requires at least one assignment",
                subject=ContractSubject.THRESHOLD,
            )
        clients = tuple(assignment.client for assignment in self.assignments)
        if len(frozenset(clients)) != len(clients):
            raise ScientificContractError(
                "threshold assignment clients must be unique",
                subject=ContractSubject.CLIENT_IDENTITY,
            )

    @property
    def clients(self) -> tuple[ClientIdentity, ...]:
        return tuple(assignment.client for assignment in self.assignments)


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionContext:
    coordinate: FederatedTrainingCoordinate
    calibration_manifest_checksum: Checksum
    score_set_checksum: Checksum
    quantile: Quantile


@runtime_checkable
class FederatedThresholdResult(Protocol):
    coordinate: FederatedTrainingCoordinate
    assignments: tuple[ThresholdAssignmentLike, ...]
    method: ClassVar[FederatedThresholdMethod]
