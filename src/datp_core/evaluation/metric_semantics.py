"""Central availability semantics for evaluation metrics."""

from datp_core.domain.enums import MetricId
from datp_core.domain.values import MetricValue, RowCount
from datp_core.evaluation.models import MetricAvailability, MetricReason, MetricStatus, UnavailableOutcome


def available(metric: MetricId, value: float, *, denominator: int | None = None) -> MetricAvailability:
    return MetricAvailability(
        metric=metric,
        status=MetricStatus.AVAILABLE,
        value=MetricValue(value),
        denominator=None if denominator is None else RowCount(denominator),
    )


def unavailable(
    metric: MetricId,
    status: MetricStatus,
    reason: MetricReason,
    *,
    denominator: int | None = None,
) -> MetricAvailability:
    if status is MetricStatus.AVAILABLE:
        raise ValueError("available status requires a numeric value")
    count = None if denominator is None else RowCount(denominator)
    return MetricAvailability(
        metric=metric,
        status=status,
        value=None,
        denominator=count,
        outcome=UnavailableOutcome(status=status, reason=reason, denominator=count),
    )
