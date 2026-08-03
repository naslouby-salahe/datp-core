"""Pooled evaluation for the independent centralized reference."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

import numpy as np

from datp_core.centralized_reference.scoring import (
    PooledScoreArtifact,
    load_score_frame,
)
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
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
    is_confirmatory_ladder_member: bool
    score_artifact_checksum: Checksum
    threshold_checksum: Checksum

    def __post_init__(self) -> None:
        if self.threshold_method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
            raise ScientificContractError(
                "centralized evaluation requires the pooled benign quantile threshold",
                subject=self.threshold_method,
            )
        if self.is_confirmatory_ladder_member:
            raise ScientificContractError(
                "centralized evaluation cannot be marked as a confirmatory ladder member",
                subject=ContractSubject.CONFIRMATORY_LADDER,
            )
        if self.evidence_role is EvidenceRole.CONFIRMATORY:
            raise ScientificContractError(
                "centralized evaluation cannot claim confirmatory evidence role",
                subject=self.evidence_role,
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
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN,
    attack_label: PopulationOutcomeLabel = PopulationOutcomeLabel.ATTACK,
) -> CentralizedEvaluationResult:
    """Evaluate pooled centralized scores under the fixed score > threshold rule."""
    _validate_evaluation_inputs(coordinate, evaluation_scores, threshold_result)
    labels, scores = _evaluation_arrays(evaluation_scores)
    predictions = scores > threshold_result.threshold.value
    confusion = _confusion_counts(labels, predictions, benign_label=benign_label, attack_label=attack_label)
    metrics = _pooled_metrics(
        labels, scores, predictions, confusion, benign_label=benign_label, attack_label=attack_label
    )
    return CentralizedEvaluationResult(
        coordinate=coordinate,
        threshold_method=threshold_result.method,
        decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
        threshold=threshold_result.threshold,
        confusion=confusion,
        metrics=metrics,
        evaluation_row_count=RowCount(int(scores.shape[0])),
        evidence_role=EvidenceRole.SUPPORTIVE,
        is_confirmatory_ladder_member=False,
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


def reject_centralized_result_in_confirmatory_ladder(result: CentralizedEvaluationResult) -> None:
    raise LeakageError(
        "centralized reference evaluation cannot enter the confirmatory B1-versus-B2 ladder",
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


def reject_b1_b4_insertion(method: FederatedThresholdMethod) -> None:
    raise LeakageError(
        "centralized reference cannot be inserted into B1-B4 federated comparisons",
        subject=method,
    )


def write_evaluation_document(evaluation: CentralizedEvaluationResult, directory: Path) -> Path:
    """Persist centralized evaluation as a typed JSON document under directory."""
    from json import dumps

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "centralized_evaluation.json"
    payload = dumps(
        {
            "threshold_method": evaluation.threshold_method.value,
            "decision_rule": evaluation.decision_rule.value,
            "threshold": evaluation.threshold.value,
            "true_negative": evaluation.confusion.true_negative.value,
            "false_positive": evaluation.confusion.false_positive.value,
            "true_positive": evaluation.confusion.true_positive.value,
            "false_negative": evaluation.confusion.false_negative.value,
            "evaluation_row_count": evaluation.evaluation_row_count.value,
            "evidence_role": evaluation.evidence_role.value,
            "is_confirmatory_ladder_member": evaluation.is_confirmatory_ladder_member,
            "metrics": [
                {
                    "metric": item.metric.value,
                    "status": item.status.value,
                    "value": item.value.value if item.value is not None else None,
                }
                for item in evaluation.metrics
            ],
        },
        indent=2,
        sort_keys=True,
    )
    path.write_text(payload + "\n", encoding="utf-8")
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
    *,
    benign_label: PopulationOutcomeLabel,
    attack_label: PopulationOutcomeLabel,
) -> CentralizedConfusionCounts:
    true_negative = 0
    false_positive = 0
    true_positive = 0
    false_negative = 0
    for label, predicted_attack in zip(labels.tolist(), predictions.tolist(), strict=True):
        label_text = str(label)
        if label_text == benign_label:
            if predicted_attack:
                false_positive += 1
            else:
                true_negative += 1
        elif label_text == attack_label:
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
    predictions: np.ndarray,
    confusion: CentralizedConfusionCounts,
    *,
    benign_label: str,
    attack_label: str,
) -> tuple[CentralizedMetricRecord, ...]:
    records: list[CentralizedMetricRecord] = []
    records.append(
        _rate_metric(
            MetricId.FALSE_POSITIVE_RATE, confusion.false_positive, confusion.false_positive + confusion.true_negative
        )
    )
    records.append(
        _rate_metric(
            MetricId.TRUE_POSITIVE_RATE, confusion.true_positive, confusion.true_positive + confusion.false_negative
        )
    )
    fpr = records[0]
    tpr = records[1]
    records.append(_balanced_accuracy(fpr, tpr))
    records.append(_binary_macro_f1(confusion))
    records.append(_pooled_macro_f1(confusion))
    records.append(_auroc(labels, scores, benign_label=benign_label, attack_label=attack_label))
    ordered = {record.metric: record for record in records}
    return tuple(ordered[metric] for metric in CENTRALIZED_POOLED_METRICS)


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
        value=MetricValue(0.5 * (tpr.value.value + specificity)),
    )


def _binary_macro_f1(confusion: CentralizedConfusionCounts) -> CentralizedMetricRecord:
    return _macro_f1_record(MetricId.BINARY_MACRO_F1, confusion)


def _pooled_macro_f1(confusion: CentralizedConfusionCounts) -> CentralizedMetricRecord:
    return _macro_f1_record(MetricId.POOLED_MACRO_F1, confusion)


def _macro_f1_record(metric: MetricId, confusion: CentralizedConfusionCounts) -> CentralizedMetricRecord:
    attack_precision_den = confusion.true_positive + confusion.false_positive
    attack_recall_den = confusion.true_positive + confusion.false_negative
    benign_precision_den = confusion.true_negative + confusion.false_negative
    benign_recall_den = confusion.true_negative + confusion.false_positive
    if min(attack_precision_den, attack_recall_den, benign_precision_den, benign_recall_den) == 0:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNAVAILABLE, value=None)
    attack_precision = confusion.true_positive.value / attack_precision_den.value
    attack_recall = confusion.true_positive.value / attack_recall_den.value
    benign_precision = confusion.true_negative.value / benign_precision_den.value
    benign_recall = confusion.true_negative.value / benign_recall_den.value
    attack_f1 = _f1(attack_precision, attack_recall)
    benign_f1 = _f1(benign_precision, benign_recall)
    if attack_f1 is None or benign_f1 is None:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNDEFINED, value=None)
    return CentralizedMetricRecord(
        metric=metric,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(0.5 * (attack_f1 + benign_f1)),
    )


def _f1(precision: float, recall: float) -> float | None:
    if precision + recall == 0:
        return None
    return 2.0 * precision * recall / (precision + recall)


def _auroc(
    labels: np.ndarray,
    scores: np.ndarray,
    *,
    benign_label: str,
    attack_label: str,
) -> CentralizedMetricRecord:
    binary = np.asarray(
        [1 if str(label) == attack_label else 0 if str(label) == benign_label else -1 for label in labels]
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
    n_pos = float(binary.sum())
    n_neg = float(binary.size - n_pos)
    if n_pos == 0.0 or n_neg == 0.0:
        return CentralizedMetricRecord(
            metric=MetricId.AUROC,
            status=AvailabilityStatus.UNAVAILABLE,
            value=None,
        )
    ranks = _average_ranks(sorted_scores)
    positive_rank_sum = float(ranks[sorted_labels == 1].sum())
    auc = (positive_rank_sum - n_pos * (n_pos + 1.0) / 2.0) / (n_pos * n_neg)
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
        average = 0.5 * (start + end - 1) + 1.0
        ranks[start:end] = average
        start = end
    return ranks
