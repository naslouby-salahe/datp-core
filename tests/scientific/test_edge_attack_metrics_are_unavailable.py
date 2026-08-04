from datp_core.domain.enums import MetricId
from datp_core.domain.values import RowCount, ScoreValue
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.models import ConfusionCounts, MetricReason, MetricStatus, UnavailableMetric
from datp_core.populations.models import PopulationOutcomeLabel


def test_unassigned_edge_attack_metrics_are_explicitly_unavailable() -> None:
    metrics = calculate_client_metrics(
        confusion=ConfusionCounts(
            true_negative=RowCount(3),
            false_positive=RowCount(1),
            true_positive=RowCount(0),
            false_negative=RowCount(0),
            attack_assignment_valid=False,
        ),
        scores=(ScoreValue(0.1), ScoreValue(0.2), ScoreValue(0.3), ScoreValue(0.9)),
        labels=(
            PopulationOutcomeLabel.BENIGN,
            PopulationOutcomeLabel.BENIGN,
            PopulationOutcomeLabel.BENIGN,
            PopulationOutcomeLabel.BENIGN,
        ),
    )
    by_metric = {item.metric: item for item in metrics}

    for metric in (MetricId.TRUE_POSITIVE_RATE, MetricId.BALANCED_ACCURACY, MetricId.BINARY_MACRO_F1, MetricId.AUROC):
        result = by_metric[metric]
        assert isinstance(result, UnavailableMetric)
        assert result.status is MetricStatus.UNAVAILABLE
        assert result.value is None
    tpr = by_metric[MetricId.TRUE_POSITIVE_RATE]
    assert isinstance(tpr, UnavailableMetric)
    assert tpr.reason is MetricReason.INVALID_ATTACK_ASSIGNMENT
