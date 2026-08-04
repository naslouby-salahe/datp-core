"""Stage: evaluate the independent centralized reference on held-out pooled scores."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

from datp_core.artifacts.store import publish_atomically
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
from datp_core.domain.values import Checksum


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


def evaluate_centralized_reference_stage(
    request: EvaluateCentralizedReferenceRequest,
) -> EvaluateCentralizedReferenceResult:
    def evaluate() -> CentralizedEvaluationResult:
        return evaluate_centralized_reference(
            coordinate=request.coordinate,
            evaluation_scores=request.evaluation_scores,
            threshold_result=request.threshold,
        )

    def write(temporary: Path) -> CentralizedEvaluationResult:
        evaluation = evaluate()
        write_evaluation_document(evaluation, temporary)
        digest = evaluation_result_checksum(evaluation)
        (temporary / CentralizedEvaluationAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        return evaluation

    outcome = publish_atomically(
        target=request.output_directory,
        overwrite=request.overwrite,
        is_reusable=lambda directory: _is_reusable(directory, request),
        write=write,
        reusable_value=lambda _directory: evaluate(),
        remove_target=rmtree,
    )
    return EvaluateCentralizedReferenceResult(
        publication_status=outcome.status,
        evaluation=outcome.value,
        complete_digest=outcome.complete_digest,
    )


def _is_reusable(directory: Path, request: EvaluateCentralizedReferenceRequest) -> bool:
    complete = directory / CentralizedEvaluationAssetName.COMPLETE
    document = directory / CentralizedEvaluationAssetName.EVALUATION
    if not (complete.is_file() and document.is_file()):
        return False
    expected = evaluation_result_checksum(
        evaluate_centralized_reference(
            coordinate=request.coordinate,
            evaluation_scores=request.evaluation_scores,
            threshold_result=request.threshold,
        )
    )
    return complete.read_text(encoding="utf-8").strip() == expected.value
