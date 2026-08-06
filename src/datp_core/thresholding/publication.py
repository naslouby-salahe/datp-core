"""Threshold artifact serialization, validation, reuse, and rebasing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values import Checksum, checksum_text
from datp_core.protocols.inference import ScoreArtifactManifest
from datp_core.protocols.temporal import TemporalDeploymentProvenance
from datp_core.thresholding.models import ThresholdConstructionResult

if TYPE_CHECKING:
    from datp_core.thresholding.dispatch import ThresholdConstructionRequest


class FederatedThresholdAssetName(StrEnum):
    RESULT = "threshold_result.json"
    TEMPORAL_PROVENANCE = "temporal_threshold_provenance.json"
    COMPLETE = "COMPLETE"


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


_RESULT_ADAPTER = TypeAdapter(ThresholdConstructionResult)


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
    try:
        result = _load_result(directory)
        provenance = _load_temporal_provenance(directory, required=request.temporal_provenance is not None)
        complete = (directory / FederatedThresholdAssetName.COMPLETE).read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return False
    if provenance != request.temporal_provenance:
        return False
    expected_result = _dispatch(request.request)
    if threshold_result_checksum(result) != threshold_result_checksum(expected_result):
        return False
    return complete == federated_threshold_publication_checksum(result, provenance).value


def load_reused_federated_threshold(
    request: FederatedThresholdPublicationRequest,
    directory: Path,
) -> ThresholdConstructionResult:
    result = _load_result(directory)
    provenance = _load_temporal_provenance(directory, required=request.temporal_provenance is not None)
    if provenance != request.temporal_provenance:
        raise ValueError("persisted temporal threshold provenance does not match the publication request")
    return result


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


def _load_result(directory: Path) -> ThresholdConstructionResult:
    path = directory / FederatedThresholdAssetName.RESULT
    return _RESULT_ADAPTER.validate_json(path.read_text(encoding="utf-8"))


def _load_temporal_provenance(
    directory: Path,
    *,
    required: bool,
) -> TemporalDeploymentProvenance | None:
    path = directory / FederatedThresholdAssetName.TEMPORAL_PROVENANCE
    if not path.exists():
        if required:
            raise ValueError("temporal threshold provenance is missing")
        return None
    if not required:
        raise ValueError("unexpected temporal threshold provenance is present")
    return TemporalDeploymentProvenance.model_validate_json(path.read_text(encoding="utf-8"))


def _dispatch(request: ThresholdConstructionRequest) -> ThresholdConstructionResult:
    from datp_core.thresholding.dispatch import dispatch_federated_threshold

    return dispatch_federated_threshold(request)
