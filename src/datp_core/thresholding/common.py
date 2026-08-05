"""Closed threshold result union and publication lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values import Checksum, Quantile, ThresholdValue, checksum_text
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.inference import ScoreArtifactManifest
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

if TYPE_CHECKING:
    from datp_core.thresholding.dispatch import ThresholdConstructionRequest


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


class FederatedThresholdAssetName(StrEnum):
    RESULT = "threshold_result.json"
    TEMPORAL_PROVENANCE = "temporal_threshold_provenance.json"
    COMPLETE = "COMPLETE"


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


@dataclass(frozen=True, slots=True)
class FederatedThresholdPublicationRequest:
    request: ThresholdConstructionRequest
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None

    def __post_init__(self) -> None:
        if (self.temporal_provenance is None) != (self.temporal_score_manifest is None):
            raise ValueError("temporal threshold construction requires both provenance and score manifest")
        if self.temporal_provenance is not None:
            if self.temporal_score_manifest is None:
                raise AssertionError("temporal publication invariant was checked")
            self.temporal_provenance.validate_score_manifest(self.temporal_score_manifest)


@dataclass(frozen=True, slots=True)
class _ThresholdPublicationProjection:
    result: ThresholdConstructionResult
    temporal_provenance: TemporalDeploymentProvenance | None


def write_federated_threshold(
    request: FederatedThresholdPublicationRequest,
    directory: Path,
) -> ThresholdConstructionResult:
    result = _dispatch(request.request)
    (directory / FederatedThresholdAssetName.RESULT).write_text(
        canonical_json_text(result),
        encoding="utf-8",
    )
    if request.temporal_provenance is not None:
        (directory / FederatedThresholdAssetName.TEMPORAL_PROVENANCE).write_text(
            canonical_json_text(request.temporal_provenance),
            encoding="utf-8",
        )
    (directory / FederatedThresholdAssetName.COMPLETE).write_text(
        federated_threshold_publication_checksum(result, request.temporal_provenance).value,
        encoding="utf-8",
    )
    return result


def federated_threshold_is_reusable(
    request: FederatedThresholdPublicationRequest,
    directory: Path,
) -> bool:
    complete = directory / FederatedThresholdAssetName.COMPLETE
    document = directory / FederatedThresholdAssetName.RESULT
    if not complete.is_file() or not document.is_file():
        return False
    provenance_document = directory / FederatedThresholdAssetName.TEMPORAL_PROVENANCE
    if (request.temporal_provenance is None and provenance_document.exists()) or (
        request.temporal_provenance is not None and not provenance_document.is_file()
    ):
        return False
    expected = federated_threshold_publication_checksum(
        _dispatch(request.request),
        request.temporal_provenance,
    )
    try:
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except OSError:
        return False


def load_reused_federated_threshold(
    request: FederatedThresholdPublicationRequest,
    directory: Path,
) -> ThresholdConstructionResult:
    del directory
    return _dispatch(request.request)


def rebase_federated_threshold(
    result: ThresholdConstructionResult,
    directory: Path,
) -> ThresholdConstructionResult:
    del directory
    return result


def threshold_result_checksum(result: ThresholdConstructionResult) -> Checksum:
    return checksum_text(canonical_json_text(result))


def federated_threshold_publication_checksum(
    result: ThresholdConstructionResult,
    temporal_provenance: TemporalDeploymentProvenance | None,
) -> Checksum:
    return checksum_text(
        canonical_json_text(
            _ThresholdPublicationProjection(
                result=result,
                temporal_provenance=temporal_provenance,
            )
        )
    )


def _dispatch(request: ThresholdConstructionRequest) -> ThresholdConstructionResult:
    from datp_core.thresholding.dispatch import dispatch_federated_threshold

    return dispatch_federated_threshold(request)
