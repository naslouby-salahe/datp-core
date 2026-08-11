from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

import numpy as np

from datp_core.analysis.metrics.models import ConfusionCounts
from datp_core.core.errors import (
    ErrorMessage,
    LeakageError,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, PartitionRole, StableRowId
from datp_core.core.numeric import RowCount, ScoreValue, ThresholdValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel


@dataclass(frozen=True, slots=True)
class _PredictionsByOutcome:
    benign: tuple[bool, ...]
    attack: tuple[bool, ...]


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
        raise LeakageError(ErrorMessage("confusion counts require held-out evaluation rows"), subject=partition_role)
    if len(scores) != len(labels) or len(scores) != len(source_row_ids):
        raise ScientificContractError(
            ErrorMessage("scores, labels, and source rows must align"), subject=ContractSubject.ROWS
        )

    if not isfinite(threshold.value):
        raise ScientificContractError(
            ErrorMessage("scores and thresholds must be finite"), subject=ContractSubject.SCORES
        )

    seen: set[StableRowId] = set()
    for row_id in source_row_ids:
        if not row_id or row_id in seen:
            raise ScientificContractError(
                ErrorMessage("evaluation source rows must be unique and stable"), subject=ContractSubject.ROWS
            )
        seen.add(row_id)

    predictions = _partition_predictions(scores, labels, threshold)
    if predictions.attack and not attack_assignment_valid:
        raise ScientificContractError(
            ErrorMessage("attack rows cannot enter a client with invalid attack assignment"),
            subject=ContractSubject.ATTACK_LABELS,
        )
    return ConfusionCounts(
        true_negative=RowCount(predictions.benign.count(False)),
        false_positive=RowCount(predictions.benign.count(True)),
        true_positive=RowCount(predictions.attack.count(True)),
        false_negative=RowCount(predictions.attack.count(False)),
        attack_assignment_valid=attack_assignment_valid,
    )


def calculate_confusion_counts_for_evaluation_arrays(
    *,
    score_values: np.ndarray,
    attack_mask: np.ndarray,
    threshold: ThresholdValue,
    attack_assignment_valid: bool,
) -> ConfusionCounts:
    if score_values.ndim != 1 or attack_mask.ndim != 1 or score_values.size != attack_mask.size:
        raise ScientificContractError(ErrorMessage("evaluation score arrays must align"), subject=ContractSubject.ROWS)
    if not isfinite(threshold.value) or not np.isfinite(score_values).all():
        raise ScientificContractError(
            ErrorMessage("scores and thresholds must be finite"), subject=ContractSubject.SCORES
        )
    predicted_attack_mask = score_values > threshold.value
    benign_mask = ~attack_mask
    if attack_mask.any() and not attack_assignment_valid:
        raise ScientificContractError(
            ErrorMessage("attack rows cannot enter a client with invalid attack assignment"),
            subject=ContractSubject.ATTACK_LABELS,
        )
    return ConfusionCounts(
        true_negative=RowCount(int(np.count_nonzero(benign_mask & ~predicted_attack_mask))),
        false_positive=RowCount(int(np.count_nonzero(benign_mask & predicted_attack_mask))),
        true_positive=RowCount(int(np.count_nonzero(attack_mask & predicted_attack_mask))),
        false_negative=RowCount(int(np.count_nonzero(attack_mask & ~predicted_attack_mask))),
        attack_assignment_valid=attack_assignment_valid,
    )


def _partition_predictions(
    scores: Sequence[ScoreValue], labels: Sequence[PopulationOutcomeLabel], threshold: ThresholdValue
) -> _PredictionsByOutcome:
    benign: list[bool] = []
    attack: list[bool] = []
    for score, label in zip(scores, labels, strict=True):
        if not isfinite(score.value):
            raise ScientificContractError(
                ErrorMessage("scores and thresholds must be finite"), subject=ContractSubject.SCORES
            )
        prediction = predicted_attack(score, threshold)
        if label is PopulationOutcomeLabel.BENIGN:
            benign.append(prediction)
        elif label is PopulationOutcomeLabel.ATTACK:
            attack.append(prediction)
        else:
            raise ScientificContractError(ErrorMessage("unrecognized evaluation label"), subject=ContractSubject.LABEL)
    return _PredictionsByOutcome(benign=tuple(benign), attack=tuple(attack))
