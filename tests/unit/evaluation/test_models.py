import pytest

from datp_core.domain.enums import MetricId
from datp_core.domain.values import MetricValue, RowCount
from datp_core.evaluation.models import MetricAvailability, MetricReason, MetricStatus, UnavailableOutcome


def test_metric_availability_requires_outcome_denominator_to_match_metric_denominator() -> None:
    with pytest.raises(ValueError, match="denominators"):
        MetricAvailability(
            MetricId.FALSE_POSITIVE_RATE,
            MetricStatus.UNAVAILABLE,
            None,
            RowCount(0),
            UnavailableOutcome(MetricStatus.UNAVAILABLE, MetricReason.EMPTY_BENIGN_DENOMINATOR, None),
        )


def test_available_metric_rejects_unavailable_outcome() -> None:
    with pytest.raises(ValueError, match="exactly one value"):
        MetricAvailability(
            MetricId.FALSE_POSITIVE_RATE,
            MetricStatus.AVAILABLE,
            MetricValue(0.1),
            outcome=UnavailableOutcome(MetricStatus.UNAVAILABLE, MetricReason.EMPTY_BENIGN_DENOMINATOR),
        )
