"""Stage: compose and publish one federated threshold cell."""

from datp_core.orchestration.commands.thresholding import (
    ConstructFederatedThresholdsRequest as _ConstructFederatedThresholdsRequest,
)
from datp_core.orchestration.commands.thresholding import (
    ConstructFederatedThresholdsResult as _ConstructFederatedThresholdsResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.thresholding.common import (
    FederatedThresholdAssetName,
    FederatedThresholdPublicationRequest,
    federated_threshold_is_reusable,
    load_reused_federated_threshold,
    rebase_federated_threshold,
    write_federated_threshold,
)


def construct_federated_thresholds_stage(
    stage_request: _ConstructFederatedThresholdsRequest,
) -> _ConstructFederatedThresholdsResult:
    publication_request = FederatedThresholdPublicationRequest(
        request=stage_request.request,
        temporal_provenance=stage_request.temporal_provenance,
        temporal_score_manifest=stage_request.temporal_score_manifest,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=stage_request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_threshold,
                validator=federated_threshold_is_reusable,
                loader=load_reused_federated_threshold,
                rebaser=rebase_federated_threshold,
            ),
            overwrite=stage_request.overwrite,
            complete_marker=FederatedThresholdAssetName.COMPLETE,
        )
    )
    return _ConstructFederatedThresholdsResult(
        result=publication.value,
        publication_status=publication.status,
        complete_digest=publication.complete_digest,
        temporal_provenance=stage_request.temporal_provenance,
    )
