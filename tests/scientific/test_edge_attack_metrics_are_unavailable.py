from datp_core.domain.enums import MetricId
from datp_core.domain.values import ScoreValue
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.models import ConfusionCounts, MetricReason, MetricStatus
from datp_core.populations.models import PopulationOutcomeLabel


def test_unassigned_edge_attack_metrics_are_explicitly_unavailable() -> None:
    metrics = calculate_client_metrics(
        confusion=ConfusionCounts(3, 1, 0, 0, False),
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
        assert result.status is MetricStatus.UNAVAILABLE
        assert result.value is None
    tpr_outcome = by_metric[MetricId.TRUE_POSITIVE_RATE].outcome
    assert tpr_outcome is not None
    assert tpr_outcome.reason is MetricReason.INVALID_ATTACK_ASSIGNMENT
