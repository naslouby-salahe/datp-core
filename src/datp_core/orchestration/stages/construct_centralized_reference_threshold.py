"""Stage: construct the pooled benign centralized threshold."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import (
    CentralizedThresholdAssetName,
    PooledThresholdResult,
    construct_pooled_benign_quantile,
    threshold_result_checksum,
    write_threshold_document,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum, checksum_file
from datp_core.orchestration.stages import _Box
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
    stage: StageOperationId
    publication_status: PublicationStatus
    threshold: PooledThresholdResult
    complete_digest: Checksum


def construct_centralized_reference_threshold_stage(
    request: ConstructCentralizedThresholdRequest,
) -> ConstructCentralizedThresholdResult:
    box = _Box[PooledThresholdResult]()

    def write(temporary: Path) -> None:
        threshold = construct_pooled_benign_quantile(
            coordinate=request.coordinate,
            calibration_scores=request.calibration_scores,
            protocol=request.protocol,
        )
        write_threshold_document(threshold, temporary)
        digest = threshold_result_checksum(threshold)
        (temporary / CentralizedThresholdAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        box.value = threshold

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, request),
            write=write,
            remove_target=lambda directory: rmtree(directory),
        )
    )
    if reused:
        threshold = construct_pooled_benign_quantile(
            coordinate=request.coordinate,
            calibration_scores=request.calibration_scores,
            protocol=request.protocol,
        )
        status = PublicationStatus.REUSED
    else:
        if box.value is None:
            raise ArtifactIntegrityError(
                "centralized threshold write did not populate a result", subject=ContractSubject.THRESHOLD
            )
        threshold = box.value
        status = PublicationStatus.PUBLISHED
    return ConstructCentralizedThresholdResult(
        stage=StageOperationId.CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD,
        publication_status=status,
        threshold=threshold,
        complete_digest=checksum_file(request.output_directory / CentralizedThresholdAssetName.COMPLETE),
    )


def _is_reusable(directory: Path, request: ConstructCentralizedThresholdRequest) -> bool:
    complete = directory / CentralizedThresholdAssetName.COMPLETE
    document = directory / CentralizedThresholdAssetName.THRESHOLD
    if not (complete.is_file() and document.is_file()):
        return False
    threshold = construct_pooled_benign_quantile(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )
    expected = threshold_result_checksum(threshold)
    return complete.read_text(encoding="utf-8").strip() == expected.value
