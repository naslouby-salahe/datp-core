"""Construct and atomically publish one federated threshold cell."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.artifacts.serialization import canonical_json_text
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file, checksum_text
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.dispatch import ThresholdConstructionRequest, dispatch_federated_threshold
from datp_core.thresholding.models import ThresholdConstructionResult


class ConstructFederatedThresholdsAssetName(StrEnum):
    RESULT = "threshold_result.json"
    TEMPORAL_PROVENANCE = "temporal_threshold_provenance.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None

    def __post_init__(self) -> None:
        if (self.temporal_provenance is None) != (self.temporal_score_manifest is None):
            raise ValueError("temporal threshold construction requires both provenance and score manifest")


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_FEDERATED_THRESHOLDS
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


@dataclass(frozen=True, slots=True)
class _ThresholdPublicationProjection:
    result: ThresholdConstructionResult
    temporal_provenance: TemporalDeploymentProvenance | None


@dataclass(frozen=True, slots=True)
class _ThresholdPublicationCodec:
    def write(
        self,
        request: ConstructFederatedThresholdsRequest,
        directory: Path,
    ) -> ThresholdConstructionResult:
        result = dispatch_federated_threshold(request.request)
        (directory / ConstructFederatedThresholdsAssetName.RESULT).write_text(
            canonical_json_text(result),
            encoding="utf-8",
        )
        if request.temporal_provenance is not None:
            (directory / ConstructFederatedThresholdsAssetName.TEMPORAL_PROVENANCE).write_text(
                canonical_json_text(request.temporal_provenance),
                encoding="utf-8",
            )
        digest = _stage_checksum(result, request.temporal_provenance)
        (directory / ConstructFederatedThresholdsAssetName.COMPLETE).write_text(
            digest.value,
            encoding="utf-8",
        )
        return result

    def validate(self, request: ConstructFederatedThresholdsRequest, directory: Path) -> bool:
        return _is_reusable(directory, request)

    def load(
        self,
        request: ConstructFederatedThresholdsRequest,
        directory: Path,
    ) -> ThresholdConstructionResult:
        return dispatch_federated_threshold(request.request)

    def rebase(
        self,
        result: ThresholdConstructionResult,
        directory: Path,
    ) -> ThresholdConstructionResult:
        return result


def threshold_result_checksum(result: ThresholdConstructionResult) -> Checksum:
    return checksum_text(canonical_json_text(result))


def _stage_checksum(
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


def construct_federated_thresholds_stage(
    stage_request: ConstructFederatedThresholdsRequest,
) -> ConstructFederatedThresholdsResult:
    _validate_temporal_request(stage_request)
    publication = publish_artifact(
        ArtifactPublication(
            target=stage_request.output_directory,
            request=stage_request,
            codec=_ThresholdPublicationCodec(),
            overwrite=stage_request.overwrite,
            complete_marker=ConstructFederatedThresholdsAssetName.COMPLETE,
        )
    )
    return ConstructFederatedThresholdsResult(
        result=publication.value,
        publication_status=publication.status,
        complete_digest=checksum_file(
            stage_request.output_directory / ConstructFederatedThresholdsAssetName.COMPLETE
        ),
        temporal_provenance=stage_request.temporal_provenance,
    )


def _is_reusable(directory: Path, stage_request: ConstructFederatedThresholdsRequest) -> bool:
    complete = directory / ConstructFederatedThresholdsAssetName.COMPLETE
    document = directory / ConstructFederatedThresholdsAssetName.RESULT
    if not (complete.is_file() and document.is_file()):
        return False
    provenance = stage_request.temporal_provenance
    provenance_document = directory / ConstructFederatedThresholdsAssetName.TEMPORAL_PROVENANCE
    if (provenance is None and provenance_document.exists()) or (
        provenance is not None and not provenance_document.is_file()
    ):
        return False
    expected = _stage_checksum(dispatch_federated_threshold(stage_request.request), provenance)
    return complete.read_text(encoding="utf-8").strip() == expected.value


def _validate_temporal_request(stage_request: ConstructFederatedThresholdsRequest) -> None:
    if stage_request.temporal_provenance is not None:
        if stage_request.temporal_score_manifest is None:
            raise AssertionError("request invariant was checked in __post_init__")
        stage_request.temporal_provenance.validate_score_manifest(stage_request.temporal_score_manifest)
