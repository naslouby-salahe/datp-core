import pytest

from datp_core.domain.enums import MetricId
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import MetricReason, MetricStatus


def test_available_preserves_numeric_denominator() -> None:
    result = available(MetricId.FALSE_POSITIVE_RATE, 0.25, denominator=8)

    assert result.value is not None
    assert result.value.value == 0.25
    assert result.denominator is not None and result.denominator.value == 8


def test_unavailable_rejects_available_status() -> None:
    with pytest.raises(ValueError, match="requires a numeric value"):
        unavailable(MetricId.FALSE_POSITIVE_RATE, MetricStatus.AVAILABLE, MetricReason.EMPTY_BENIGN_DENOMINATOR)
