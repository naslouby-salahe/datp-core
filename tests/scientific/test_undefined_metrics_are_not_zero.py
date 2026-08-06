from datp_core.domain.enums import MetricId
from datp_core.domain.values.counts import RowCount
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.models import ConfusionCounts, MetricReason, MetricStatus, UnavailableMetric


def test_empty_class_metrics_remain_typed_unavailable_or_undefined_not_zero() -> None:
    metrics = calculate_client_metrics(
        confusion=ConfusionCounts(
            true_negative=RowCount(0),
            false_positive=RowCount(0),
            true_positive=RowCount(0),
            false_negative=RowCount(0),
            attack_assignment_valid=True,
        ),
        scores=(),
        labels=(),
    )
    by_metric = {item.metric: item for item in metrics}

    assert by_metric[MetricId.FALSE_POSITIVE_RATE].status is MetricStatus.UNAVAILABLE
    assert by_metric[MetricId.TRUE_POSITIVE_RATE].status is MetricStatus.UNAVAILABLE
    macro_f1 = by_metric[MetricId.BINARY_MACRO_F1]
    assert isinstance(macro_f1, UnavailableMetric)
    assert macro_f1.status is MetricStatus.UNDEFINED
    assert macro_f1.value is None
    assert macro_f1.reason is MetricReason.UNDEFINED_CLASS_F1
