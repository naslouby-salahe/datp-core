"""Stage: evaluate the independent centralized reference on held-out pooled scores."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.centralized_reference.evaluation import (
    CentralizedEvaluationResult,
    evaluate_centralized_reference,
    evaluation_result_checksum,
    reject_centralized_result_in_confirmatory_ladder,
)
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file


class CentralizedEvaluationAssetName:
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


def evaluate_centralized_reference_stage(
    request: EvaluateCentralizedReferenceRequest,
) -> EvaluateCentralizedReferenceResult:
    holder: dict[str, CentralizedEvaluationResult] = {}

    def write(temporary: Path) -> None:
        evaluation = evaluate_centralized_reference(
            coordinate=request.coordinate,
            evaluation_scores=request.evaluation_scores,
            threshold_result=request.threshold,
        )
        if evaluation.is_confirmatory_ladder_member:
            reject_centralized_result_in_confirmatory_ladder(evaluation)
        _write_evaluation_document(evaluation, temporary)
        digest = evaluation_result_checksum(evaluation)
        (temporary / CentralizedEvaluationAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        holder["evaluation"] = evaluation

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
        evaluation = holder["evaluation"]
        status = PublicationStatus.PUBLISHED
    return EvaluateCentralizedReferenceResult(
        stage=StageOperationId.EVALUATE_CENTRALIZED_REFERENCE,
        publication_status=status,
        evaluation=evaluation,
        complete_digest=checksum_file(request.output_directory / CentralizedEvaluationAssetName.COMPLETE),
    )


def _write_evaluation_document(evaluation: CentralizedEvaluationResult, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CentralizedEvaluationAssetName.EVALUATION
    metrics = ",\n".join(
        (
            "    {"
            f'"metric": "{item.metric.value}", '
            f'"status": "{item.status.value}", '
            f'"value": {("null" if item.value is None else item.value.value)}'
            "}"
        )
        for item in evaluation.metrics
    )
    payload = (
        "{\n"
        f'  "threshold_method": "{evaluation.threshold_method.value}",\n'
        f'  "decision_rule": "{evaluation.decision_rule.value}",\n'
        f'  "threshold": {evaluation.threshold.value},\n'
        f'  "true_negative": {evaluation.confusion.true_negative},\n'
        f'  "false_positive": {evaluation.confusion.false_positive},\n'
        f'  "true_positive": {evaluation.confusion.true_positive},\n'
        f'  "false_negative": {evaluation.confusion.false_negative},\n'
        f'  "evaluation_row_count": {evaluation.evaluation_row_count},\n'
        f'  "evidence_role": "{evaluation.evidence_role.value}",\n'
        f'  "is_confirmatory_ladder_member": false,\n'
        f'  "metrics": [\n{metrics}\n  ]\n'
        "}\n"
    )
    path.write_text(payload, encoding="utf-8")
    return path


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
