import pytest

from datp_core.domain.enums import MetricId
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.ratios import MetricValue
from datp_core.evaluation.models import AvailableMetric, MetricReason, MetricStatus, UnavailableMetric, WarningCode


def test_warning_code_member_set_is_exact_and_unique() -> None:
    assert set(WarningCode.__members__) == {
        "NEAR_ZERO_MEAN_FPR",
        "UNDEFINED_COEFFICIENT_OF_VARIATION",
        "UNAVAILABLE_ATTACK_ASSIGNMENT",
        "INVALID_TEMPORAL_CHRONOLOGY",
        "UNRESOLVED_CLUSTER_ASSIGNMENTS",
        "MISSING_TRAFFIC_RATE_EVIDENCE",
    }
    values = tuple(member.value for member in WarningCode)
    assert len(values) == len(set(values))
    assert all(value.islower() for value in values)


def test_available_metric_contains_only_available_state() -> None:
    metric = AvailableMetric(
        metric=MetricId.FALSE_POSITIVE_RATE,
        value=MetricValue(0.1),
        denominator=RowCount(10),
    )

    assert metric.status is MetricStatus.AVAILABLE
    assert metric.reason is None


def test_unavailable_metric_contains_only_unavailable_state() -> None:
    metric = UnavailableMetric(
        metric=MetricId.FALSE_POSITIVE_RATE,
        status=MetricStatus.UNAVAILABLE,
        reason=MetricReason.EMPTY_BENIGN_DENOMINATOR,
        denominator=RowCount(0),
    )

    assert metric.value is None
    assert metric.denominator == RowCount(0)


def test_unavailable_metric_rejects_available_status() -> None:
    with pytest.raises(ValueError, match="AvailableMetric"):
        UnavailableMetric(
            metric=MetricId.FALSE_POSITIVE_RATE,
            status=MetricStatus.AVAILABLE,
            reason=MetricReason.EMPTY_BENIGN_DENOMINATOR,
        )
