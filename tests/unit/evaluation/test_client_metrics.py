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
