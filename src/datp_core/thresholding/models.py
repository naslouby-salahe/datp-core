"""Pure threshold result and assignment contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.ratios import Quantile, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.methods.cluster import GroupedThresholdResult
from datp_core.thresholding.methods.conformal import ConformalThresholdResult
from datp_core.thresholding.methods.family import FamilyThresholdResult
from datp_core.thresholding.methods.federated_statistics import FederatedStatisticsThresholdResult
from datp_core.thresholding.methods.local import LocalThresholdResult
from datp_core.thresholding.methods.shared import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
)
from datp_core.thresholding.methods.shrinkage import ShrinkageThresholdResult

type ThresholdConstructionResult = (
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
                "threshold assignment set requires at least one assignment",
                subject=ContractSubject.THRESHOLD,
            )
        clients = tuple(item.client for item in self.assignments)
        if len(frozenset(clients)) != len(clients):
            raise ScientificContractError(
                "threshold assignment clients must be unique",
                subject=ContractSubject.CLIENT_IDENTITY,
            )

    @property
    def clients(self) -> tuple[ClientIdentity, ...]:
        return tuple(item.client for item in self.assignments)


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
