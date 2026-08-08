"""Threshold artifact serialization, validation, reuse, and rebasing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import TypeAdapter

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.artifacts.provenance import Checksum, checksum_text
from datp_core.artifacts.repositories.publication import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.identifiers import PublicationStatus
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.dispatch import ThresholdConstructionRequest, ThresholdConstructionResult

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


class FederatedThresholdAssetName(StrEnum):
    RESULT = "threshold_result.json"
    TEMPORAL_PROVENANCE = "temporal_threshold_provenance.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class FederatedThresholdPublicationRequest:
    request: ThresholdConstructionRequest
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: FederatedScoreArtifactManifest | None = None

    def __post_init__(self) -> None:
        if (self.temporal_provenance is None) != (self.temporal_score_manifest is None):
            raise ValueError("temporal threshold construction requires both provenance and score manifest")
        if self.temporal_provenance is not None:
            if self.temporal_score_manifest is None:
                raise AssertionError("temporal publication invariant was checked")
            self.temporal_provenance.validate_score_manifest(self.temporal_score_manifest)


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedThresholdConstructionRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: FederatedScoreArtifactManifest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedThresholdConstructionResult:
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


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


def construct_and_publish_federated_thresholds(
    request: FederatedThresholdConstructionRequest,
) -> FederatedThresholdConstructionResult:
    publication_request = FederatedThresholdPublicationRequest(
        request=request.request,
        temporal_provenance=request.temporal_provenance,
        temporal_score_manifest=request.temporal_score_manifest,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_threshold,
                validator=federated_threshold_is_reusable,
                loader=load_reused_federated_threshold,
                rebaser=rebase_federated_threshold,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedThresholdAssetName.COMPLETE,
        )
    )
    return FederatedThresholdConstructionResult(
        result=publication.value,
        publication_status=publication.status,
        complete_digest=publication.complete_digest,
        temporal_provenance=request.temporal_provenance,
    )


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
    adapter: TypeAdapter[ThresholdConstructionResult] = TypeAdapter(ThresholdConstructionResult)
    return adapter.validate_json(path.read_text(encoding="utf-8"))


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
    from datp_core.thresholds.dispatch import dispatch_federated_threshold

    return dispatch_federated_threshold(request)
