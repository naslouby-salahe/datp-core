from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

import numpy as np

from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.confusion import calculate_confusion_counts
from datp_core.analysis.metrics.models import ConfusionCounts, MetricAvailability
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    CentralizedThresholdMethod,
    ContractSubject,
    EvidenceRole,
    FileContentText,
    MetricId,
    OutcomeLabel,
    OutcomeLabelSequence,
    PartitionRole,
    QuantileInterpolationSemantics,
    ScoreFrameColumn,
    StableRowId,
    ValidationReasonText,
)
from datp_core.core.numeric import Quantile, RowCount, ScoreValue, ThresholdValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.data.populations.integrity import reject_non_benign_labels
from datp_core.detector.scoring.centralized import load_score_frame, reject_non_finite_scores
from datp_core.detector.scoring.models import PooledScoreArtifact
from datp_core.detector.training.centralized import CentralizedTrainingCoordinate
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.protocols import CANONICAL_QUANTILE, CentralizedQuantileProtocol


class CentralizedThresholdAssetName(StrEnum):
    THRESHOLD = "pooled_threshold.json"


class CentralizedDecisionRule(StrEnum):
    SCORE_STRICTLY_GREATER_THAN_THRESHOLD = "score_strictly_greater_than_threshold"


class CentralizedEvaluationPublicationAsset(StrEnum):
    EVALUATION = "centralized_evaluation.json"


CENTRALIZED_POOLED_QUANTILE_PROTOCOL = CentralizedQuantileProtocol(
    method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
    quantile=CANONICAL_QUANTILE,
)
CENTRALIZED_POOLED_METRICS = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
    MetricId.AVERAGE_PRECISION,
    MetricId.POOLED_MACRO_F1,
)


@dataclass(frozen=True, slots=True)
class PooledThresholdResult:
    coordinate: CentralizedTrainingCoordinate
    method: CentralizedThresholdMethod
    quantile: Quantile
    quantile_interpolation: QuantileInterpolationSemantics
    threshold: ThresholdValue
    calibration_score_count: RowCount


class PooledThresholdDocument(StrictModel):
    method: CentralizedThresholdMethod
    quantile: Quantile
    quantile_interpolation: QuantileInterpolationSemantics
    threshold: ThresholdValue
    calibration_score_count: RowCount

    @classmethod
    def from_result(cls, result: PooledThresholdResult) -> "PooledThresholdDocument":
        return cls(
            method=result.method,
            quantile=result.quantile,
            quantile_interpolation=result.quantile_interpolation,
            threshold=result.threshold,
            calibration_score_count=result.calibration_score_count,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCentralizedThresholdRequest:
    coordinate: CentralizedTrainingCoordinate
    calibration_scores: PooledScoreArtifact
    output_directory: Path
    protocol: CentralizedQuantileProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCentralizedThresholdResult:
    threshold: PooledThresholdResult


@dataclass(frozen=True, slots=True)
class CentralizedEvaluationResult:
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: ConfusionCounts
    metrics: tuple[MetricAvailability, ...]
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole


class CentralizedEvaluationDocument(StrictModel):
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: ConfusionCounts
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole
    metrics: tuple[MetricAvailability, ...]

    @classmethod
    def from_result(cls, result: CentralizedEvaluationResult) -> "CentralizedEvaluationDocument":
        return cls(
            coordinate=result.coordinate,
            threshold_method=result.threshold_method,
            decision_rule=result.decision_rule,
            threshold=result.threshold,
            confusion=result.confusion,
            evaluation_row_count=result.evaluation_row_count,
            evidence_role=result.evidence_role,
            metrics=result.metrics,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedDetectorRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedDetectorResult:
    evaluation: CentralizedEvaluationResult


def construct_centralized_threshold(
    request: ConstructCentralizedThresholdRequest,
) -> ConstructCentralizedThresholdResult:
    if request.output_directory.exists() and not request.overwrite:
        raise FileExistsError(f"threshold output already exists: {request.output_directory}")
    threshold = construct_pooled_benign_quantile(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )
    write_text_atomically(
        request.output_directory / CentralizedThresholdAssetName.THRESHOLD,
        FileContentText(canonical_json_text(PooledThresholdDocument.from_result(threshold))),
    )
    return ConstructCentralizedThresholdResult(threshold=threshold)


def construct_pooled_benign_quantile(
    *,
    coordinate: CentralizedTrainingCoordinate,
    calibration_scores: PooledScoreArtifact,
    protocol: CentralizedQuantileProtocol,
) -> PooledThresholdResult:
    if (
        calibration_scores.coordinate != coordinate
        or calibration_scores.partition_role is not PartitionRole.CALIBRATION
    ):
        raise ScientificContractError(
            ErrorMessage("centralized threshold requires calibration scores for its coordinate")
        )
    if protocol.method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
        raise ScientificContractError(ErrorMessage("centralized threshold protocol must be pooled benign quantile"))
    scores = _benign_calibration_scores(calibration_scores)
    return PooledThresholdResult(
        coordinate=coordinate,
        method=protocol.method,
        quantile=protocol.quantile,
        quantile_interpolation=QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR,
        threshold=exact_pooled_quantile(scores, protocol.quantile),
        calibration_score_count=RowCount(int(scores.size)),
    )


def evaluate_centralized_detector(request: EvaluateCentralizedDetectorRequest) -> EvaluateCentralizedDetectorResult:
    if request.output_directory.exists() and not request.overwrite:
        raise FileExistsError(f"evaluation output already exists: {request.output_directory}")
    evaluation = evaluate_centralized_reference(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold_result=request.threshold,
    )
    write_text_atomically(
        request.output_directory / CentralizedEvaluationPublicationAsset.EVALUATION,
        FileContentText(canonical_json_text(CentralizedEvaluationDocument.from_result(evaluation))),
    )
    return EvaluateCentralizedDetectorResult(evaluation=evaluation)


def evaluate_centralized_reference(
    *,
    coordinate: CentralizedTrainingCoordinate,
    evaluation_scores: PooledScoreArtifact,
    threshold_result: PooledThresholdResult,
) -> CentralizedEvaluationResult:
    if evaluation_scores.coordinate != coordinate or threshold_result.coordinate != coordinate:
        raise ScientificContractError(
            ErrorMessage("evaluation coordinate mismatch"), subject=ContractSubject.COORDINATE
        )
    if evaluation_scores.partition_role is not PartitionRole.EVALUATION:
        raise ScientificContractError(ErrorMessage("centralized evaluation requires evaluation scores"))
    frame = load_score_frame(evaluation_scores)
    row_ids = tuple(
        StableRowId(str(value)) for value in frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).to_list()
    )
    labels = tuple(
        PopulationOutcomeLabel(str(value)) for value in frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list()
    )
    scores = tuple(
        ScoreValue(float(value)) for value in frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list()
    )
    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=row_ids,
        threshold=threshold_result.threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=True,
    )
    metrics = calculate_client_metrics(confusion=confusion, scores=scores, labels=labels)
    binary_macro_f1 = next(item for item in metrics if item.metric is MetricId.BINARY_MACRO_F1)
    return CentralizedEvaluationResult(
        coordinate=coordinate,
        threshold_method=threshold_result.method,
        decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
        threshold=threshold_result.threshold,
        confusion=confusion,
        metrics=(*metrics, replace(binary_macro_f1, metric=MetricId.POOLED_MACRO_F1)),
        evaluation_row_count=confusion.evaluation_row_count,
        evidence_role=EvidenceRole.SUPPORTIVE,
    )


def exact_pooled_quantile(scores: np.ndarray, quantile: Quantile) -> ThresholdValue:
    if scores.ndim != 1 or scores.size == 0:
        raise ScientificContractError(ErrorMessage("quantile requires a non-empty score array"))
    value = float(np.quantile(scores, quantile.value, method="linear"))
    if not np.isfinite(value):
        raise ScientificContractError(ErrorMessage("quantile result must be finite"))
    return ThresholdValue(value)


def _benign_calibration_scores(scores: PooledScoreArtifact) -> np.ndarray:
    frame = load_score_frame(scores)
    labels = OutcomeLabelSequence(
        tuple(OutcomeLabel(str(value)) for value in frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list())
    )
    reject_non_benign_labels(
        tuple(PopulationOutcomeLabel(str(label)) for label in labels),
        message=ValidationReasonText("attack-labelled rows cannot enter centralized benign calibration"),
        subject=ContractSubject.LABEL,
        benign_label=PopulationOutcomeLabel.BENIGN,
    )
    values = np.asarray(frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list(), dtype=np.float64)
    reject_non_finite_scores(
        values,
        message=ErrorMessage("calibration scores must be finite"),
        subject=ContractSubject.CALIBRATION,
    )
    return values
