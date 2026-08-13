import pytest

from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.models import ConfusionCounts, MetricStatus
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import RowCount, ScoreValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel


def test_client_metrics_preserve_undefined_attack_metrics() -> None:
    result = calculate_client_metrics(
        confusion=ConfusionCounts(
            true_negative=RowCount(3),
            false_positive=RowCount(0),
            true_positive=RowCount(0),
            false_negative=RowCount(0),
            attack_assignment_valid=False,
        ),
        scores=(ScoreValue(0.1), ScoreValue(0.2), ScoreValue(0.3)),
        labels=(PopulationOutcomeLabel.BENIGN,) * 3,
    )
    values = {item.metric: item for item in result}

    assert values[MetricId.FALSE_POSITIVE_RATE].value is not None
    assert values[MetricId.TRUE_POSITIVE_RATE].status is MetricStatus.UNAVAILABLE
    assert values[MetricId.BALANCED_ACCURACY].value is None
    assert values[MetricId.BINARY_MACRO_F1].value is None
    assert values[MetricId.AUROC].value is None
    assert values[MetricId.AVERAGE_PRECISION].value is None


def test_average_precision_uses_the_standard_descending_score_step_integral() -> None:
    result = calculate_client_metrics(
        confusion=ConfusionCounts(
            true_negative=RowCount(1),
            false_positive=RowCount(0),
            true_positive=RowCount(2),
            false_negative=RowCount(0),
            attack_assignment_valid=True,
        ),
        scores=(ScoreValue(0.9), ScoreValue(0.8), ScoreValue(0.7)),
        labels=(
            PopulationOutcomeLabel.ATTACK,
            PopulationOutcomeLabel.BENIGN,
            PopulationOutcomeLabel.ATTACK,
        ),
    )
    values = {item.metric: item for item in result}

    average_precision = values[MetricId.AVERAGE_PRECISION].value
    assert average_precision is not None
    assert average_precision.value == pytest.approx(5.0 / 6.0)


def test_average_precision_groups_tied_scores_at_one_distinct_threshold() -> None:
    confusion = ConfusionCounts(
        true_negative=RowCount(1),
        false_positive=RowCount(0),
        true_positive=RowCount(2),
        false_negative=RowCount(0),
        attack_assignment_valid=True,
    )
    labels = (
        PopulationOutcomeLabel.ATTACK,
        PopulationOutcomeLabel.BENIGN,
        PopulationOutcomeLabel.ATTACK,
    )
    forward = calculate_client_metrics(
        confusion=confusion,
        scores=(ScoreValue(0.9), ScoreValue(0.9), ScoreValue(0.8)),
        labels=labels,
    )
    reversed_tie = calculate_client_metrics(
        confusion=confusion,
        scores=(ScoreValue(0.9), ScoreValue(0.9), ScoreValue(0.8)),
        labels=(labels[1], labels[0], labels[2]),
    )

    forward_value = {item.metric: item for item in forward}[MetricId.AVERAGE_PRECISION].value
    reversed_value = {item.metric: item for item in reversed_tie}[MetricId.AVERAGE_PRECISION].value

    assert forward_value is not None
    assert reversed_value is not None
    assert forward_value.value == pytest.approx(7.0 / 12.0)
    assert reversed_value.value == forward_value.value
