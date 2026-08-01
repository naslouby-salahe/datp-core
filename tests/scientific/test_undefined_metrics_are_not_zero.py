from datp_core.domain.enums import MetricId
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.models import ConfusionCounts, MetricReason, MetricStatus


def test_empty_class_metrics_remain_typed_unavailable_or_undefined_not_zero() -> None:
    metrics = calculate_client_metrics(confusion=ConfusionCounts(0, 0, 0, 0, True), scores=(), labels=())
    by_metric = {item.metric: item for item in metrics}

    assert by_metric[MetricId.FALSE_POSITIVE_RATE].status is MetricStatus.UNAVAILABLE
    assert by_metric[MetricId.TRUE_POSITIVE_RATE].status is MetricStatus.UNAVAILABLE
    macro_f1 = by_metric[MetricId.BINARY_MACRO_F1]
    assert macro_f1.status is MetricStatus.UNDEFINED
    assert macro_f1.value is None
    assert macro_f1.outcome is not None and macro_f1.outcome.reason is MetricReason.UNDEFINED_CLASS_F1
