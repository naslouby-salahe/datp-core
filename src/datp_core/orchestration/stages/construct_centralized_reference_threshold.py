"""Stage: compose pooled benign centralized threshold publication."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import (
    CentralizedThresholdAssetName,
    CentralizedThresholdPublicationRequest,
    PooledThresholdResult,
    centralized_threshold_is_reusable,
    load_reused_centralized_threshold,
    rebase_centralized_threshold,
    write_centralized_threshold,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
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
    publication_request = CentralizedThresholdPublicationRequest(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_threshold,
                validator=centralized_threshold_is_reusable,
                loader=load_reused_centralized_threshold,
                rebaser=rebase_centralized_threshold,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructCentralizedThresholdResult(
        publication_status=publication.status,
        threshold=publication.value,
        complete_digest=checksum_file(request.output_directory / CentralizedThresholdAssetName.COMPLETE),
    )
