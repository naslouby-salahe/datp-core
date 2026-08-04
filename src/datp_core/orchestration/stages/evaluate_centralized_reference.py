"""Stage: evaluate the independent centralized reference on held-out pooled scores."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from datp_core.centralized_reference.evaluation import (
    CentralizedEvaluationResult,
    evaluate_centralized_reference,
    evaluation_result_checksum,
    write_evaluation_document,
)
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact


class CentralizedEvaluationAssetName(StrEnum):
    EVALUATION = "centralized_evaluation.json"
    COMPLETE = "COMPLETE"


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


@dataclass(frozen=True, slots=True)
class _CentralizedEvaluationCodec:
    def write(
        self,
        request: EvaluateCentralizedReferenceRequest,
        directory: Path,
    ) -> CentralizedEvaluationResult:
        evaluation = _evaluate(request)
        write_evaluation_document(evaluation, directory)
        digest = evaluation_result_checksum(evaluation)
        (directory / CentralizedEvaluationAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        return evaluation

    def validate(self, request: EvaluateCentralizedReferenceRequest, directory: Path) -> bool:
        return _is_reusable(directory, request)

    def load(
        self,
        request: EvaluateCentralizedReferenceRequest,
        directory: Path,
    ) -> CentralizedEvaluationResult:
        return _evaluate(request)

    def rebase(
        self,
        result: CentralizedEvaluationResult,
        directory: Path,
    ) -> CentralizedEvaluationResult:
        return result


def evaluate_centralized_reference_stage(
    request: EvaluateCentralizedReferenceRequest,
) -> EvaluateCentralizedReferenceResult:
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=_CentralizedEvaluationCodec(),
            overwrite=request.overwrite,
            complete_marker=CentralizedEvaluationAssetName.COMPLETE,
        )
    )
    return EvaluateCentralizedReferenceResult(
        publication_status=publication.status,
        evaluation=publication.value,
        complete_digest=checksum_file(request.output_directory / CentralizedEvaluationAssetName.COMPLETE),
    )


def _evaluate(request: EvaluateCentralizedReferenceRequest) -> CentralizedEvaluationResult:
    return evaluate_centralized_reference(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold_result=request.threshold,
    )


def _is_reusable(directory: Path, request: EvaluateCentralizedReferenceRequest) -> bool:
    complete = directory / CentralizedEvaluationAssetName.COMPLETE
    document = directory / CentralizedEvaluationAssetName.EVALUATION
    if not (complete.is_file() and document.is_file()):
        return False
    expected = evaluation_result_checksum(_evaluate(request))
    return complete.read_text(encoding="utf-8").strip() == expected.value
