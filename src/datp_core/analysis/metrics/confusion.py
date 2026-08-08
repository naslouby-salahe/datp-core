"""Strict held-out prediction and confusion-count semantics."""

from collections.abc import Sequence
from math import isfinite

from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import ContractSubject, PartitionRole, StableRowId
from datp_core.core.numeric import RowCount, ScoreValue, ThresholdValue
from datp_core.evaluation.models import ConfusionCounts


def predicted_attack(score: ScoreValue, threshold: ThresholdValue) -> bool:
    return score.exceeds(threshold)


def calculate_confusion_counts(
    *,
    scores: Sequence[ScoreValue],
    labels: Sequence[PopulationOutcomeLabel],
    source_row_ids: Sequence[StableRowId],
    threshold: ThresholdValue,
    partition_role: PartitionRole,
    attack_assignment_valid: bool,
) -> ConfusionCounts:
    if partition_role is not PartitionRole.EVALUATION:
        raise LeakageError("confusion counts require held-out evaluation rows", subject=partition_role)
    if len(scores) != len(labels) or len(scores) != len(source_row_ids):
        raise ScientificContractError("scores, labels, and source rows must align", subject=ContractSubject.ROWS)

    if not isfinite(threshold.value):
        raise ScientificContractError("scores and thresholds must be finite", subject=ContractSubject.SCORES)

    seen: set[StableRowId] = set()
    for row_id in source_row_ids:
        if not row_id or row_id in seen:
            raise ScientificContractError(
                "evaluation source rows must be unique and stable", subject=ContractSubject.ROWS
            )
        seen.add(row_id)

    benign_predictions, attack_predictions = _partition_predictions(scores, labels, threshold)
    if attack_predictions and not attack_assignment_valid:
        raise ScientificContractError(
            "attack rows cannot enter a client with invalid attack assignment",
            subject=ContractSubject.ATTACK_LABELS,
        )
    return ConfusionCounts(
        true_negative=RowCount(benign_predictions.count(False)),
        false_positive=RowCount(benign_predictions.count(True)),
        true_positive=RowCount(attack_predictions.count(True)),
        false_negative=RowCount(attack_predictions.count(False)),
        attack_assignment_valid=attack_assignment_valid,
    )


def _partition_predictions(
    scores: Sequence[ScoreValue], labels: Sequence[PopulationOutcomeLabel], threshold: ThresholdValue
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    benign: list[bool] = []
    attack: list[bool] = []
    for score, label in zip(scores, labels, strict=True):
        if not isfinite(score.value):
            raise ScientificContractError("scores and thresholds must be finite", subject=ContractSubject.SCORES)
        prediction = predicted_attack(score, threshold)
        if label is PopulationOutcomeLabel.BENIGN:
            benign.append(prediction)
        elif label is PopulationOutcomeLabel.ATTACK:
            attack.append(prediction)
        else:
            raise ScientificContractError("unrecognized evaluation label", subject=ContractSubject.LABEL)
    return tuple(benign), tuple(attack)
