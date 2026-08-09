"""Per-client held-out metrics with no implicit undefined-to-zero conversion."""

from collections.abc import Sequence
from math import isfinite

import numpy as np

from datp_core.analysis.metrics.fixed_score import FederatedEvaluationScoreArrays
from datp_core.analysis.metrics.models import ConfusionCounts, MetricAvailability, MetricReason, MetricStatus
from datp_core.analysis.metrics.semantics import available, unavailable
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, MetricId
from datp_core.core.numeric import MetricValue, RowCount, ScoreValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel

CLIENT_METRICS: tuple[MetricId, ...] = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
)


def calculate_client_metrics(
    *,
    confusion: ConfusionCounts,
    scores: Sequence[ScoreValue],
    labels: Sequence[PopulationOutcomeLabel],
) -> tuple[MetricAvailability, ...]:
    """Evaluate one client; AUROC uses continuous scores, never threshold predictions."""
    if len(scores) != len(labels) or len(scores) != confusion.evaluation_row_count.value:
        raise ScientificContractError(
            ErrorMessage("client scores, labels, and confusion counts must align"), subject=ContractSubject.ROWS
        )

    score_values = np.fromiter((score.value for score in scores), dtype=np.float64, count=len(scores))

    if not np.isfinite(score_values).all():
        raise ScientificContractError(
            ErrorMessage("client evaluation scores must be finite"), subject=ContractSubject.SCORES
        )

    fpr = _rate(MetricId.FALSE_POSITIVE_RATE, confusion.false_positive, confusion.benign_denominator)
    tpr = _attack_rate(confusion)

    return (
        fpr,
        tpr,
        _balanced_accuracy(fpr, tpr),
        _binary_macro_f1(confusion),
        _auroc(score_values, labels, confusion.attack_assignment_valid),
    )


def calculate_metrics_for_evaluation_score_arrays(
    *,
    confusion: ConfusionCounts,
    score_arrays: FederatedEvaluationScoreArrays,
) -> tuple[MetricAvailability, ...]:
    """Evaluate client metrics from one validated federated score artifact."""
    return calculate_client_metrics(
        confusion=confusion,
        scores=score_arrays.scores,
        labels=score_arrays.labels,
    )


def _rate(metric: MetricId, numerator: RowCount, denominator: RowCount) -> MetricAvailability:
    if denominator.value == 0:
        return unavailable(
            metric,
            MetricStatus.UNAVAILABLE,
            MetricReason.EMPTY_BENIGN_DENOMINATOR,
            denominator=RowCount(0),
        )
    return available(metric, MetricValue(numerator.value / denominator.value), denominator=denominator)


def _attack_rate(confusion: ConfusionCounts) -> MetricAvailability:
    denominator = confusion.attack_denominator
    if not confusion.attack_assignment_valid:
        return unavailable(
            MetricId.TRUE_POSITIVE_RATE,
            MetricStatus.UNAVAILABLE,
            MetricReason.INVALID_ATTACK_ASSIGNMENT,
            denominator=denominator,
        )
    if denominator.value == 0:
        return unavailable(
            MetricId.TRUE_POSITIVE_RATE,
            MetricStatus.UNAVAILABLE,
            MetricReason.EMPTY_ATTACK_DENOMINATOR,
            denominator=RowCount(0),
        )
    return available(
        MetricId.TRUE_POSITIVE_RATE,
        MetricValue(confusion.true_positive.value / denominator.value),
        denominator=denominator,
    )


def _balanced_accuracy(fpr: MetricAvailability, tpr: MetricAvailability) -> MetricAvailability:
    if fpr.value is None or tpr.value is None:
        return unavailable(
            MetricId.BALANCED_ACCURACY,
            MetricStatus.UNAVAILABLE,
            MetricReason.MISSING_CAPABILITY,
        )
    return available(MetricId.BALANCED_ACCURACY, MetricValue((tpr.value.value + (1.0 - fpr.value.value)) / 2.0))


def _binary_macro_f1(confusion: ConfusionCounts) -> MetricAvailability:
    if not confusion.attack_assignment_valid:
        return unavailable(
            MetricId.BINARY_MACRO_F1,
            MetricStatus.UNAVAILABLE,
            MetricReason.INVALID_ATTACK_ASSIGNMENT,
        )
    true_positive = confusion.true_positive.value
    false_positive = confusion.false_positive.value
    false_negative = confusion.false_negative.value
    true_negative = confusion.true_negative.value

    attack_denominator = 2 * true_positive + false_positive + false_negative
    benign_denominator = 2 * true_negative + false_positive + false_negative

    if attack_denominator == 0 or benign_denominator == 0:
        return unavailable(
            MetricId.BINARY_MACRO_F1,
            MetricStatus.UNDEFINED,
            MetricReason.UNDEFINED_CLASS_F1,
        )

    attack_f1 = 2.0 * true_positive / attack_denominator
    benign_f1 = 2.0 * true_negative / benign_denominator
    return available(MetricId.BINARY_MACRO_F1, MetricValue((attack_f1 + benign_f1) / 2.0))


def _auroc(
    score_values: np.ndarray, labels: Sequence[PopulationOutcomeLabel], attack_assignment_valid: bool
) -> MetricAvailability:
    if not attack_assignment_valid:
        return unavailable(MetricId.AUROC, MetricStatus.UNAVAILABLE, MetricReason.INVALID_ATTACK_ASSIGNMENT)

    binary = np.fromiter(
        (1 if label is PopulationOutcomeLabel.ATTACK else 0 for label in labels), dtype=np.int64, count=len(labels)
    )
    positives = int(binary.sum())
    negatives = int(binary.size - positives)

    if positives == 0 or negatives == 0:
        return unavailable(
            MetricId.AUROC,
            MetricStatus.UNAVAILABLE,
            MetricReason.SINGLE_CLASS_SCORES,
            denominator=RowCount(binary.size),
        )

    order = np.argsort(score_values, kind="mergesort")
    sorted_scores = score_values[order]
    ranks = _average_ranks(sorted_scores)
    positive_rank_sum = float(ranks[binary[order] == 1].sum())
    value = (positive_rank_sum - positives * (positives + 1.0) / 2.0) / (positives * negatives)

    if not isfinite(value):
        return unavailable(MetricId.AUROC, MetricStatus.UNDEFINED, MetricReason.MISSING_CAPABILITY)
    return available(MetricId.AUROC, MetricValue(value), denominator=RowCount(binary.size))


def _average_ranks(sorted_scores: np.ndarray) -> np.ndarray:
    if sorted_scores.size == 0:
        return np.empty(0, dtype=np.float64)

    diffs = sorted_scores[1:] != sorted_scores[:-1]
    change_indices = np.nonzero(diffs)[0] + 1

    ends = np.append(change_indices, sorted_scores.size)
    starts = np.insert(change_indices, 0, 0)

    avg_ranks = 0.5 * (starts + ends + 1.0)
    counts = ends - starts

    return np.repeat(avg_ranks, counts)
