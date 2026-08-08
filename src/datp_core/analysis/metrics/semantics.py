"""Central availability semantics for evaluation metrics."""

from datp_core.analysis.metrics.models import (
    AvailableMetric,
    MetricAvailability,
    MetricReason,
    MetricStatus,
    UnavailableMetric,
)
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import MetricValue, RowCount


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
