"""Central availability semantics for evaluation metrics."""

from datp_core.domain.enums import MetricId
from datp_core.domain.values import MetricValue, RowCount
from datp_core.evaluation.models import AvailableMetric, MetricAvailability, MetricReason, MetricStatus, UnavailableMetric


def available(metric: MetricId, value: float, *, denominator: int | None = None) -> AvailableMetric:
    return AvailableMetric(
        metric=metric,
        value=MetricValue(value),
        denominator=None if denominator is None else RowCount(denominator),
    )


def unavailable(
    metric: MetricId,
    status: MetricStatus,
    reason: MetricReason,
    *,
    denominator: int | None = None,
) -> UnavailableMetric:
    return UnavailableMetric(
        metric=metric,
        status=status,
        reason=reason,
        denominator=None if denominator is None else RowCount(denominator),
    )


def metric_value(metric: MetricAvailability) -> float | None:
    return None if metric.value is None else metric.value.value
