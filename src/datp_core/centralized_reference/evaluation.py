"""Pooled evaluation for the independent centralized reference."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

import numpy as np

from datp_core.artifacts.serialization import serialize_json_model
from datp_core.centralized_reference.scoring import PooledScoreArtifact, load_score_frame
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    CentralizedThresholdMethod,
    ContractSubject,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    ScoreFrameColumn,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, RowCount, ThresholdValue, checksum_text
from datp_core.populations.models import PopulationOutcomeLabel

BENIGN_OUTCOME_LABEL = PopulationOutcomeLabel.BENIGN
ATTACK_OUTCOME_LABEL = PopulationOutcomeLabel.ATTACK
BINARY_CLASS_MEAN_WEIGHT = 0.5
F1_NUMERATOR_FACTOR = 2.0
RANK_POSITION_OFFSET = 1.0


class CentralizedDecisionRule(StrEnum):
    SCORE_STRICTLY_GREATER_THAN_THRESHOLD = "score_strictly_greater_than_threshold"


@dataclass(frozen=True, slots=True)
class CentralizedConfusionCounts:
    true_negative: RowCount
    false_positive: RowCount
    true_positive: RowCount
    false_negative: RowCount

    def __post_init__(self) -> None:
        for name, value in (
            ("true_negative", self.true_negative),
            ("false_positive", self.false_positive),
            ("true_positive", self.true_positive),
            ("false_negative", self.false_negative),
        ):
            if not isinstance(value, RowCount):
                raise TypeError(f"{name} must be a RowCount")


@dataclass(frozen=True, slots=True)
class CentralizedMetricRecord:
    metric: MetricId
    status: AvailabilityStatus
    value: MetricValue | None

    def __post_init__(self) -> None:
        if self.status is AvailabilityStatus.AVAILABLE:
            if self.value is None:
                raise ValueError("available metrics require a numeric value")
        elif self.value is not None:
            raise ValueError("unavailable or undefined metrics must not carry a numeric value")


@dataclass(frozen=True, slots=True)
class CentralizedEvaluationResult:
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: CentralizedConfusionCounts
    metrics: tuple[CentralizedMetricRecord, ...]
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole
    score_artifact_checksum: Checksum
    threshold_checksum: Checksum

    def __post_init__(self) -> None:
        if self.threshold_method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
            raise ScientificContractError(
                "centralized evaluation requires the pooled benign quantile threshold",
                subject=self.threshold_method,
            )
        if self.evidence_role is EvidenceRole.CONFIRMATORY:
            raise ScientificContractError(
                "centralized evaluation cannot claim confirmatory evidence role",
                subject=self.evidence_role,
            )
        if tuple(record.metric for record in self.metrics) != CENTRALIZED_POOLED_METRICS:
            raise ScientificContractError(
                "centralized evaluation metrics must follow the declared pooled metric order",
                subject=ContractSubject.METRICS,
            )


class CentralizedMetricDocument(StrictModel):
    metric: MetricId
    status: AvailabilityStatus
    value: MetricValue | None


class CentralizedEvaluationDocument(StrictModel):
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: CentralizedConfusionCounts
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole
    score_artifact_checksum: Checksum
    threshold_checksum: Checksum
    metrics: tuple[CentralizedMetricDocument, ...]

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
            score_artifact_checksum=result.score_artifact_checksum,
            threshold_checksum=result.threshold_checksum,
            metrics=tuple(
                CentralizedMetricDocument(
                    metric=record.metric,
                    status=record.status,
                    value=record.value,
                )
                for record in result.metrics
            ),
        )


CENTRALIZED_POOLED_METRICS = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
    MetricId.POOLED_MACRO_F1,
)


def evaluate_centralized_reference(
    *,
    coordinate: CentralizedTrainingCoordinate,
    evaluation_scores: PooledScoreArtifact,
    threshold_result: PooledThresholdResult,
) -> CentralizedEvaluationResult:
    """Evaluate pooled centralized scores under the fixed score > threshold rule."""
    _validate_evaluation_inputs(coordinate, evaluation_scores, threshold_result)
    labels, scores = _evaluation_arrays(evaluation_scores)
    predictions = scores > threshold_result.threshold.value
    confusion = _confusion_counts(labels, predictions)
    metrics = _pooled_metrics(labels, scores, confusion)
    return CentralizedEvaluationResult(
        coordinate=coordinate,
        threshold_method=threshold_result.method,
        decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
        threshold=threshold_result.threshold,
        confusion=confusion,
        metrics=metrics,
        evaluation_row_count=RowCount(int(scores.shape[0])),
        evidence_role=EvidenceRole.SUPPORTIVE,
        score_artifact_checksum=evaluation_scores.checksum,
        threshold_checksum=checksum_text(
            f"{threshold_result.threshold.value}|{threshold_result.score_artifact_checksum.value}"
        ),
    )


def _validate_evaluation_inputs(
    coordinate: CentralizedTrainingCoordinate,
    evaluation_scores: PooledScoreArtifact,
    threshold_result: PooledThresholdResult,
) -> None:
    if evaluation_scores.coordinate != coordinate or threshold_result.coordinate != coordinate:
        raise ScientificContractError("evaluation coordinate mismatch", subject=ContractSubject.COORDINATE)
    if evaluation_scores.partition_role is not PartitionRole.EVALUATION:
        raise ScientificContractError(
            "centralized evaluation requires evaluation scores",
            subject=evaluation_scores.partition_role,
        )
    if threshold_result.method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
        raise ScientificContractError(
            "centralized evaluation requires the pooled benign quantile",
            subject=threshold_result.method,
        )


def _evaluation_arrays(evaluation_scores: PooledScoreArtifact) -> tuple[np.ndarray, np.ndarray]:
    frame = load_score_frame(evaluation_scores)
    labels = np.asarray(frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list(), dtype=object)
    scores = np.asarray(
        frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list(),
        dtype=np.float64,
    )
    if scores.shape[0] != labels.shape[0]:
        raise ScientificContractError("evaluation scores and labels must align", subject=ContractSubject.ROWS)
    if not np.isfinite(scores).all():
        raise ScientificContractError("evaluation scores must be finite", subject=ContractSubject.SCORES)
    return labels, scores


def reject_centralized_result_in_confirmatory_threshold_comparison(
    result: CentralizedEvaluationResult,
) -> None:
    raise LeakageError(
        "centralized reference evaluation cannot enter the confirmatory shared-versus-local threshold comparison",
        subject=result.threshold_method,
    )


def reject_centralized_as_federated_threshold_policy(method: CentralizedThresholdMethod) -> None:
    raise LeakageError(
        "centralized pooled quantile is not a federated threshold policy",
        subject=method,
    )


def reject_cross_client_cv_fpr_from_pooled_centralized() -> None:
    raise LeakageError(
        "confirmatory cross-client CV(FPR) cannot be computed from the pooled centralized result",
        subject=MetricId.FPR_COEFFICIENT_OF_VARIATION,
    )


def reject_centralized_in_federated_threshold_comparison(method: FederatedThresholdMethod) -> None:
    raise LeakageError(
        "centralized reference cannot be inserted into federated threshold-policy comparisons",
        subject=method,
    )


def write_evaluation_document(evaluation: CentralizedEvaluationResult, directory: Path) -> Path:
    """Persist centralized evaluation through the strict canonical JSON boundary."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "centralized_evaluation.json"
    serialize_json_model(CentralizedEvaluationDocument.from_result(evaluation), path)
    return path


def evaluation_result_checksum(result: CentralizedEvaluationResult) -> Checksum:
    metric_payload = "|".join(
        f"{item.metric.value}:{item.status.value}:{'' if item.value is None else item.value.value}"
        for item in result.metrics
    )
    return checksum_text(
        f"{result.confusion.true_negative.value},{result.confusion.false_positive.value},"
        f"{result.confusion.true_positive.value},{result.confusion.false_negative.value}|{metric_payload}"
    )


def _confusion_counts(
    labels: np.ndarray,
    predictions: np.ndarray,
) -> CentralizedConfusionCounts:
    true_negative = 0
    false_positive = 0
    true_positive = 0
    false_negative = 0
    for label, predicted_attack in zip(labels.tolist(), predictions.tolist(), strict=True):
        label_text = str(label)
        if label_text == BENIGN_OUTCOME_LABEL:
            if predicted_attack:
                false_positive += 1
            else:
                true_negative += 1
        elif label_text == ATTACK_OUTCOME_LABEL:
            if predicted_attack:
                true_positive += 1
            else:
                false_negative += 1
        else:
            raise ScientificContractError(
                f"unrecognized evaluation label {label_text!r}",
                subject=ContractSubject.LABEL,
            )
    return CentralizedConfusionCounts(
        true_negative=RowCount(true_negative),
        false_positive=RowCount(false_positive),
        true_positive=RowCount(true_positive),
        false_negative=RowCount(false_negative),
    )


def _pooled_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    confusion: CentralizedConfusionCounts,
) -> tuple[CentralizedMetricRecord, ...]:
    false_positive_rate = _rate_metric(
        MetricId.FALSE_POSITIVE_RATE,
        confusion.false_positive,
        confusion.false_positive + confusion.true_negative,
    )
    true_positive_rate = _rate_metric(
        MetricId.TRUE_POSITIVE_RATE,
        confusion.true_positive,
        confusion.true_positive + confusion.false_negative,
    )
    return (
        false_positive_rate,
        true_positive_rate,
        _balanced_accuracy(false_positive_rate, true_positive_rate),
        _macro_f1_record(MetricId.BINARY_MACRO_F1, confusion),
        _auroc(labels, scores),
        _macro_f1_record(MetricId.POOLED_MACRO_F1, confusion),
    )


def _rate_metric(metric: MetricId, numerator: RowCount, denominator: RowCount) -> CentralizedMetricRecord:
    if denominator == 0:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNAVAILABLE, value=None)
    return CentralizedMetricRecord(
        metric=metric,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(numerator.value / denominator.value),
    )


def _balanced_accuracy(
    fpr: CentralizedMetricRecord,
    tpr: CentralizedMetricRecord,
) -> CentralizedMetricRecord:
    if fpr.status is not AvailabilityStatus.AVAILABLE or tpr.status is not AvailabilityStatus.AVAILABLE:
        return CentralizedMetricRecord(
            metric=MetricId.BALANCED_ACCURACY,
            status=AvailabilityStatus.UNAVAILABLE,
            value=None,
        )
    if fpr.value is None or tpr.value is None:
        return CentralizedMetricRecord(
            metric=MetricId.BALANCED_ACCURACY,
            status=AvailabilityStatus.UNAVAILABLE,
            value=None,
        )
    specificity = 1.0 - fpr.value.value
    return CentralizedMetricRecord(
        metric=MetricId.BALANCED_ACCURACY,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(BINARY_CLASS_MEAN_WEIGHT * (tpr.value.value + specificity)),
    )


def _macro_f1_record(metric: MetricId, confusion: CentralizedConfusionCounts) -> CentralizedMetricRecord:
    attack_precision_denominator = confusion.true_positive + confusion.false_positive
    attack_recall_denominator = confusion.true_positive + confusion.false_negative
    benign_precision_denominator = confusion.true_negative + confusion.false_negative
    benign_recall_denominator = confusion.true_negative + confusion.false_positive
    denominators = (
        attack_precision_denominator,
        attack_recall_denominator,
        benign_precision_denominator,
        benign_recall_denominator,
    )
    if min(denominators) == 0:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNAVAILABLE, value=None)
    attack_precision = confusion.true_positive.value / attack_precision_denominator.value
    attack_recall = confusion.true_positive.value / attack_recall_denominator.value
    benign_precision = confusion.true_negative.value / benign_precision_denominator.value
    benign_recall = confusion.true_negative.value / benign_recall_denominator.value
    attack_f1 = _f1(attack_precision, attack_recall)
    benign_f1 = _f1(benign_precision, benign_recall)
    if attack_f1 is None or benign_f1 is None:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNDEFINED, value=None)
    return CentralizedMetricRecord(
        metric=metric,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(BINARY_CLASS_MEAN_WEIGHT * (attack_f1 + benign_f1)),
    )


def _f1(precision: float, recall: float) -> float | None:
    total = precision + recall
    if total == 0:
        return None
    return F1_NUMERATOR_FACTOR * precision * recall / total


def _auroc(labels: np.ndarray, scores: np.ndarray) -> CentralizedMetricRecord:
    binary = np.asarray(
        [
            1
            if str(label) == ATTACK_OUTCOME_LABEL
            else 0
            if str(label) == BENIGN_OUTCOME_LABEL
            else -1
            for label in labels
        ]
    )
    if np.any(binary < 0):
        raise ScientificContractError("AUROC encountered unrecognized labels", subject=ContractSubject.LABEL)
    if binary.min() == binary.max():
        return CentralizedMetricRecord(
            metric=MetricId.AUROC,
            status=AvailabilityStatus.UNAVAILABLE,
            value=None,
        )
    order = np.argsort(scores, kind="mergesort")
    sorted_labels = binary[order]
    sorted_scores = scores[order]
    positive_count = float(binary.sum())
    negative_count = float(binary.size - positive_count)
    if positive_count == 0.0 or negative_count == 0.0:
        return CentralizedMetricRecord(
            metric=MetricId.AUROC,
            status=AvailabilityStatus.UNAVAILABLE,
            value=None,
        )
    ranks = _average_ranks(sorted_scores)
    positive_rank_sum = float(ranks[sorted_labels == 1].sum())
    auc = (
        positive_rank_sum
        - positive_count * (positive_count + RANK_POSITION_OFFSET) / F1_NUMERATOR_FACTOR
    ) / (positive_count * negative_count)
    if not isfinite(auc):
        return CentralizedMetricRecord(
            metric=MetricId.AUROC,
            status=AvailabilityStatus.UNDEFINED,
            value=None,
        )
    return CentralizedMetricRecord(
        metric=MetricId.AUROC,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(auc),
    )


def _average_ranks(sorted_scores: np.ndarray) -> np.ndarray:
    ranks = np.empty(sorted_scores.shape[0], dtype=np.float64)
    start = 0
    while start < sorted_scores.shape[0]:
        end = start + 1
        while end < sorted_scores.shape[0] and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average = BINARY_CLASS_MEAN_WEIGHT * (start + end - 1) + RANK_POSITION_OFFSET
        ranks[start:end] = average
        start = end
    return ranks
