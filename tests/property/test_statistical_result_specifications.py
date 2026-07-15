from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.evaluation.statistical_results import (
    ConfidenceLevel,
    StatisticalMethod,
    ValidBootstrapIntervalResult,
)


@given(
    lower=st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
    upper=st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
)
def test_bootstrap_interval_direction_properties_are_derived_from_bounds(lower: float, upper: float) -> None:
    lower_bound, upper_bound = sorted((lower, upper))
    interval = ValidBootstrapIntervalResult(
        method=StatisticalMethod.BCA_BOOTSTRAP,
        point_estimate=(lower_bound + upper_bound) / 2,
        lower=lower_bound,
        upper=upper_bound,
        confidence=ConfidenceLevel(value=Decimal("0.95")),
        resamples=BootstrapResampleCount(value=100),
    )

    assert interval.excludes_zero is (upper_bound < 0 or lower_bound > 0)
    assert interval.direction_positive is (lower_bound > 0)
