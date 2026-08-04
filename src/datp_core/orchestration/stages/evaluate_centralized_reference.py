"""Stage: compose independent centralized held-out evaluation publication."""

from datp_core.evaluation.operational import (
    CentralizedEvaluationPublicationAsset,
    CentralizedEvaluationPublicationRequest,
    centralized_evaluation_is_reusable,
    load_reused_centralized_evaluation,
    rebase_centralized_evaluation,
    write_centralized_evaluation,
)
from datp_core.orchestration.commands.evaluation import (
    EvaluateCentralizedReferenceRequest as _EvaluateCentralizedReferenceRequest,
    EvaluateCentralizedReferenceResult as _EvaluateCentralizedReferenceResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)


def evaluate_centralized_reference_stage(
    request: _EvaluateCentralizedReferenceRequest,
) -> _EvaluateCentralizedReferenceResult:
    publication_request = CentralizedEvaluationPublicationRequest(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold=request.threshold,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_evaluation,
                validator=centralized_evaluation_is_reusable,
                loader=load_reused_centralized_evaluation,
                rebaser=rebase_centralized_evaluation,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedEvaluationPublicationAsset.COMPLETE,
        )
    )
    return _EvaluateCentralizedReferenceResult(
        publication_status=publication.status,
        evaluation=publication.value,
        complete_digest=publication.complete_digest,
    )
