import pytest

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.domain.enums import PartitionRole
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import ScoreValue, ThresholdValue
from datp_core.evaluation.confusion import calculate_confusion_counts, predicted_attack


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
        source_row_ids=("a", "b", "c", "d"),
        threshold=threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=True,
    )

    assert predicted_attack(ScoreValue(2.0), threshold) is False
    assert (result.true_negative, result.false_positive, result.true_positive, result.false_negative) == (2, 0, 2, 0)
    assert result.evaluation_row_count.value == 4


def test_confusion_rejects_calibration_and_duplicate_source_rows() -> None:
    with pytest.raises(LeakageError):
        calculate_confusion_counts(
            scores=(ScoreValue(1.0),),
            labels=(PopulationOutcomeLabel.BENIGN,),
            source_row_ids=("a",),
            threshold=ThresholdValue(1.0),
            partition_role=PartitionRole.CALIBRATION,
            attack_assignment_valid=True,
        )
    with pytest.raises(ScientificContractError):
        calculate_confusion_counts(
            scores=(ScoreValue(1.0), ScoreValue(2.0)),
            labels=(PopulationOutcomeLabel.BENIGN, PopulationOutcomeLabel.BENIGN),
            source_row_ids=("a", "a"),
            threshold=ThresholdValue(1.0),
            partition_role=PartitionRole.EVALUATION,
            attack_assignment_valid=True,
        )
