import pytest

from datp_core.analysis.metrics.models import MetricReason, MetricStatus
from datp_core.analysis.metrics.semantics import available, unavailable
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import MetricValue, RowCount


def test_available_preserves_numeric_denominator() -> None:
    result = available(MetricId.FALSE_POSITIVE_RATE, MetricValue(0.25), denominator=RowCount(8))

    assert result.value.value == 0.25
    assert result.denominator is not None
    assert result.denominator.value == 8


def test_unavailable_rejects_available_status() -> None:
    with pytest.raises(ValueError, match="available status requires an AvailableMetric"):
        unavailable(MetricId.FALSE_POSITIVE_RATE, MetricStatus.AVAILABLE, MetricReason.EMPTY_BENIGN_DENOMINATOR)
