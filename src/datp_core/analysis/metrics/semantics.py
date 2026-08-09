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


def available(
    metric: MetricId,
    value: MetricValue | float,
    *,
    denominator: RowCount | None = None,
) -> AvailableMetric:
    metric_value = value if type(value) is MetricValue else MetricValue(float(value))
    return AvailableMetric(
        metric=metric,
        value=metric_value,
        denominator=denominator,
    )


def unavailable(
    metric: MetricId,
    status: MetricStatus,
    reason: MetricReason,
    *,
    denominator: RowCount | None = None,
) -> UnavailableMetric:
    return UnavailableMetric(
        metric=metric,
        status=status,
        reason=reason,
        denominator=denominator,
    )


def metric_value(metric: MetricAvailability) -> MetricValue | None:
    return metric.value
