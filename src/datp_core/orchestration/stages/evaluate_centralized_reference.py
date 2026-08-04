"""Stage: compose independent centralized held-out evaluation publication."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.centralized_reference.evaluation import CentralizedEvaluationResult
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file
from datp_core.evaluation.operational import (
    CentralizedEvaluationPublicationAsset,
    CentralizedEvaluationPublicationRequest,
    centralized_evaluation_is_reusable,
    load_reused_centralized_evaluation,
    rebase_centralized_evaluation,
    write_centralized_evaluation,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)


@dataclass(frozen=True, slots=True)
class EvaluateCentralizedReferenceRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class EvaluateCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.EVALUATE_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    evaluation: CentralizedEvaluationResult
    complete_digest: Checksum


def evaluate_centralized_reference_stage(
    request: EvaluateCentralizedReferenceRequest,
) -> EvaluateCentralizedReferenceResult:
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
    return EvaluateCentralizedReferenceResult(
        publication_status=publication.status,
        evaluation=publication.value,
        complete_digest=checksum_file(
            request.output_directory / CentralizedEvaluationPublicationAsset.COMPLETE
        ),
    )
