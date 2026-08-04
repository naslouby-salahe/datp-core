"""Stage: construct the pooled benign centralized threshold."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import (
    CentralizedThresholdAssetName,
    PooledThresholdResult,
    construct_pooled_benign_quantile,
    threshold_result_checksum,
    write_threshold_document,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact
from datp_core.protocols.models import CentralizedQuantileProtocol


@dataclass(frozen=True, slots=True)
class ConstructCentralizedThresholdRequest:
    coordinate: CentralizedTrainingCoordinate
    calibration_scores: PooledScoreArtifact
    output_directory: Path
    protocol: CentralizedQuantileProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ConstructCentralizedThresholdResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD
    publication_status: PublicationStatus
    threshold: PooledThresholdResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class _CentralizedThresholdCodec:
    def write(
        self,
        request: ConstructCentralizedThresholdRequest,
        directory: Path,
    ) -> PooledThresholdResult:
        threshold = _construct(request)
        write_threshold_document(threshold, directory)
        digest = threshold_result_checksum(threshold)
        (directory / CentralizedThresholdAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        return threshold

    def validate(self, request: ConstructCentralizedThresholdRequest, directory: Path) -> bool:
        return _is_reusable(directory, request)

    def load(
        self,
        request: ConstructCentralizedThresholdRequest,
        directory: Path,
    ) -> PooledThresholdResult:
        return _construct(request)

    def rebase(self, result: PooledThresholdResult, directory: Path) -> PooledThresholdResult:
        return result


def construct_centralized_reference_threshold_stage(
    request: ConstructCentralizedThresholdRequest,
) -> ConstructCentralizedThresholdResult:
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=_CentralizedThresholdCodec(),
            overwrite=request.overwrite,
            complete_marker=CentralizedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructCentralizedThresholdResult(
        publication_status=publication.status,
        threshold=publication.value,
        complete_digest=checksum_file(request.output_directory / CentralizedThresholdAssetName.COMPLETE),
    )


def _construct(request: ConstructCentralizedThresholdRequest) -> PooledThresholdResult:
    return construct_pooled_benign_quantile(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )


def _is_reusable(directory: Path, request: ConstructCentralizedThresholdRequest) -> bool:
    complete = directory / CentralizedThresholdAssetName.COMPLETE
    document = directory / CentralizedThresholdAssetName.THRESHOLD
    if not (complete.is_file() and document.is_file()):
        return False
    expected = threshold_result_checksum(_construct(request))
    return complete.read_text(encoding="utf-8").strip() == expected.value
