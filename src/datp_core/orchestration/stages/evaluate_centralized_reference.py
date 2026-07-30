"""Stage: evaluate the independent centralized reference on held-out pooled scores."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.centralized_reference.evaluation import (
    CentralizedEvaluationResult,
    evaluate_centralized_reference,
    evaluation_result_checksum,
    write_evaluation_document,
)
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum, checksum_file


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
    stage: StageOperationId
    publication_status: PublicationStatus
    evaluation: CentralizedEvaluationResult
    complete_digest: Checksum


@dataclass
class _EvaluationBox:
    evaluation: CentralizedEvaluationResult | None = None


def evaluate_centralized_reference_stage(
    request: EvaluateCentralizedReferenceRequest,
) -> EvaluateCentralizedReferenceResult:
    box = _EvaluationBox()

    def write(temporary: Path) -> None:
        evaluation = evaluate_centralized_reference(
            coordinate=request.coordinate,
            evaluation_scores=request.evaluation_scores,
            threshold_result=request.threshold,
        )
        write_evaluation_document(evaluation, temporary)
        digest = evaluation_result_checksum(evaluation)
        (temporary / CentralizedEvaluationAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        box.evaluation = evaluation

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
        evaluation = evaluate_centralized_reference(
            coordinate=request.coordinate,
            evaluation_scores=request.evaluation_scores,
            threshold_result=request.threshold,
        )
        status = PublicationStatus.REUSED
    else:
        if box.evaluation is None:
            raise ArtifactIntegrityError(
                "centralized evaluation write did not populate a result",
                subject=ContractSubject.THRESHOLD,
            )
        evaluation = box.evaluation
        status = PublicationStatus.PUBLISHED
    return EvaluateCentralizedReferenceResult(
        stage=StageOperationId.EVALUATE_CENTRALIZED_REFERENCE,
        publication_status=status,
        evaluation=evaluation,
        complete_digest=checksum_file(request.output_directory / CentralizedEvaluationAssetName.COMPLETE),
    )


def _is_reusable(directory: Path, request: EvaluateCentralizedReferenceRequest) -> bool:
    complete = directory / CentralizedEvaluationAssetName.COMPLETE
    document = directory / CentralizedEvaluationAssetName.EVALUATION
    if not (complete.is_file() and document.is_file()):
        return False
    evaluation = evaluate_centralized_reference(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold_result=request.threshold,
    )
    expected = evaluation_result_checksum(evaluation)
    return complete.read_text(encoding="utf-8").strip() == expected.value
