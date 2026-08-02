"""Strict held-out prediction and confusion-count semantics."""

from collections.abc import Sequence
from math import isfinite

from datp_core.domain.enums import ContractSubject, PartitionRole
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import ScoreValue, ThresholdValue
from datp_core.evaluation.models import ConfusionCounts
from datp_core.populations.models import PopulationOutcomeLabel


def predicted_attack(score: ScoreValue, threshold: ThresholdValue) -> bool:
    """The sole global operating rule: reconstruction error strictly exceeds threshold."""
    return score > threshold


def calculate_confusion_counts(
    *,
    scores: Sequence[ScoreValue],
    labels: Sequence[PopulationOutcomeLabel],
    source_row_ids: Sequence[str],
    threshold: ThresholdValue,
    partition_role: PartitionRole,
    attack_assignment_valid: bool,
) -> ConfusionCounts:
    if partition_role is not PartitionRole.EVALUATION:
        raise LeakageError("confusion counts require held-out evaluation rows", subject=partition_role)
    if len(scores) != len(labels) or len(scores) != len(source_row_ids):
        raise ScientificContractError("scores, labels, and source rows must align", subject=ContractSubject.ROWS)
    if len(source_row_ids) != len(frozenset(source_row_ids)) or any(not value for value in source_row_ids):
        raise ScientificContractError("evaluation source rows must be unique and stable", subject=ContractSubject.ROWS)
    if not isfinite(threshold.value) or any(not isfinite(score.value) for score in scores):
        raise ScientificContractError("scores and thresholds must be finite", subject=ContractSubject.SCORES)
    benign_predictions, attack_predictions = _partition_predictions(scores, labels, threshold)
    if attack_predictions and not attack_assignment_valid:
        raise ScientificContractError(
            "attack rows cannot enter a client with invalid attack assignment",
            subject=ContractSubject.ATTACK_LABELS,
        )
    return ConfusionCounts(
        true_negative=sum(not prediction for prediction in benign_predictions),
        false_positive=sum(benign_predictions),
        true_positive=sum(attack_predictions),
        false_negative=sum(not prediction for prediction in attack_predictions),
        attack_assignment_valid=attack_assignment_valid,
    )


def _partition_predictions(
    scores: Sequence[ScoreValue], labels: Sequence[PopulationOutcomeLabel], threshold: ThresholdValue
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    benign: list[bool] = []
    attack: list[bool] = []
    for score, label in zip(scores, labels, strict=True):
        prediction = predicted_attack(score, threshold)
        if label is PopulationOutcomeLabel.BENIGN:
            benign.append(prediction)
        elif label is PopulationOutcomeLabel.ATTACK:
            attack.append(prediction)
        else:
            raise ScientificContractError("unrecognized evaluation label", subject=ContractSubject.LABEL)
    return tuple(benign), tuple(attack)
