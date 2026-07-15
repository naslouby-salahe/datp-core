from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.evaluation.statistical_results import ConfidenceLevel, ValidBootstrapIntervalResult
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.statistics.scipy_adapter import BcaBootstrapRequest, SciPyStatisticsAdapter


@given(
    st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=4,
        max_size=8,
        unique=True,
    )
)
def test_bca_interval_is_ordered_and_contains_the_point_estimate(values: list[float]) -> None:
    result = SciPyStatisticsAdapter().bca_bootstrap(
        BcaBootstrapRequest(
            values=tuple(values),
            confidence=ConfidenceLevel(value=Decimal("0.95")),
            resamples=BootstrapResampleCount(value=200),
            bootstrap_seed=Seed(value=17),
        )
    )

    if isinstance(result, ValidBootstrapIntervalResult):
        assert result.lower <= result.point_estimate <= result.upper
