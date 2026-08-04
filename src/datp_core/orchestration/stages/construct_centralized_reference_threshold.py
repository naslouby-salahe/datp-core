"""Stage: construct the pooled benign centralized threshold."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

from datp_core.artifacts.store import publish_atomically
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
from datp_core.domain.values import Checksum
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


def construct_centralized_reference_threshold_stage(
    request: ConstructCentralizedThresholdRequest,
) -> ConstructCentralizedThresholdResult:
    def construct() -> PooledThresholdResult:
        return construct_pooled_benign_quantile(
            coordinate=request.coordinate,
            calibration_scores=request.calibration_scores,
            protocol=request.protocol,
        )

    def write(temporary: Path) -> PooledThresholdResult:
        threshold = construct()
        write_threshold_document(threshold, temporary)
        digest = threshold_result_checksum(threshold)
        (temporary / CentralizedThresholdAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        return threshold

    outcome = publish_atomically(
        target=request.output_directory,
        overwrite=request.overwrite,
        is_reusable=lambda directory: _is_reusable(directory, request),
        write=write,
        reusable_value=lambda _directory: construct(),
        remove_target=rmtree,
    )
    return ConstructCentralizedThresholdResult(
        publication_status=outcome.status,
        threshold=outcome.value,
        complete_digest=outcome.complete_digest,
    )


def _is_reusable(directory: Path, request: ConstructCentralizedThresholdRequest) -> bool:
    complete = directory / CentralizedThresholdAssetName.COMPLETE
    document = directory / CentralizedThresholdAssetName.THRESHOLD
    if not (complete.is_file() and document.is_file()):
        return False
    expected = threshold_result_checksum(
        construct_pooled_benign_quantile(
            coordinate=request.coordinate,
            calibration_scores=request.calibration_scores,
            protocol=request.protocol,
        )
    )
    return complete.read_text(encoding="utf-8").strip() == expected.value
