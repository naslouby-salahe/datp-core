import numpy as np
import pytest

from datp_core.analysis.metrics.confusion import (
    calculate_confusion_counts,
    calculate_confusion_counts_for_evaluation_arrays,
    predicted_attack,
)
from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import PartitionRole, StableRowId
from datp_core.core.numeric import ScoreValue, ThresholdValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel


def test_prediction_boundary_is_benign_and_counts_conserve_rows() -> None:
    threshold = ThresholdValue(2.0)
    scores = (ScoreValue(1.0), ScoreValue(2.0), ScoreValue(3.0), ScoreValue(4.0))
    labels = (
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.ATTACK,
        PopulationOutcomeLabel.ATTACK,
    )

    result = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=(StableRowId("a"), StableRowId("b"), StableRowId("c"), StableRowId("d")),
        threshold=threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=True,
    )

    assert predicted_attack(ScoreValue(2.0), threshold) is False
    assert (
        result.true_negative.value,
        result.false_positive.value,
        result.true_positive.value,
        result.false_negative.value,
    ) == (2, 0, 2, 0)
    assert result.evaluation_row_count.value == 4


def test_confusion_rejects_calibration_and_duplicate_source_rows() -> None:
    calibration_scores = (ScoreValue(1.0),)
    calibration_source_row_ids = (StableRowId("a"),)
    threshold = ThresholdValue(1.0)
    with pytest.raises(LeakageError):
        calculate_confusion_counts(
            scores=calibration_scores,
            labels=(PopulationOutcomeLabel.BENIGN,),
            source_row_ids=calibration_source_row_ids,
            threshold=threshold,
            partition_role=PartitionRole.CALIBRATION,
            attack_assignment_valid=True,
        )


def test_numeric_evaluation_arrays_match_semantic_confusion_counts() -> None:
    threshold = ThresholdValue(2.0)
    scores = (ScoreValue(1.0), ScoreValue(2.0), ScoreValue(3.0), ScoreValue(4.0))
    labels = (
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.ATTACK,
        PopulationOutcomeLabel.ATTACK,
    )
    semantic = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=(StableRowId("a"), StableRowId("b"), StableRowId("c"), StableRowId("d")),
        threshold=threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=True,
    )
    numeric = calculate_confusion_counts_for_evaluation_arrays(
        score_values=np.array([1.0, 2.0, 3.0, 4.0]),
        attack_mask=np.array([False, False, True, True]),
        threshold=threshold,
        attack_assignment_valid=True,
    )

    assert numeric == semantic
    duplicate_scores = (ScoreValue(1.0), ScoreValue(2.0))
    duplicate_source_row_ids = (StableRowId("a"), StableRowId("a"))
    with pytest.raises(ScientificContractError):
        calculate_confusion_counts(
            scores=duplicate_scores,
            labels=(PopulationOutcomeLabel.BENIGN, PopulationOutcomeLabel.BENIGN),
            source_row_ids=duplicate_source_row_ids,
            threshold=threshold,
            partition_role=PartitionRole.EVALUATION,
            attack_assignment_valid=True,
        )
