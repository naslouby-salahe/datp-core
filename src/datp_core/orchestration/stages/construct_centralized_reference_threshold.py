"""Stage: compose pooled benign centralized threshold publication."""

from datp_core.centralized_reference.thresholding import (
    CentralizedThresholdAssetName,
    CentralizedThresholdPublicationRequest,
    centralized_threshold_is_reusable,
    load_reused_centralized_threshold,
    rebase_centralized_threshold,
    write_centralized_threshold,
)
from datp_core.orchestration.commands.thresholding import (
    ConstructCentralizedThresholdRequest as _ConstructCentralizedThresholdRequest,
    ConstructCentralizedThresholdResult as _ConstructCentralizedThresholdResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)


def construct_centralized_reference_threshold_stage(
    request: _ConstructCentralizedThresholdRequest,
) -> _ConstructCentralizedThresholdResult:
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
    return _ConstructCentralizedThresholdResult(
        publication_status=publication.status,
        threshold=publication.value,
        complete_digest=publication.complete_digest,
    )
