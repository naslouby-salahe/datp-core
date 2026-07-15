from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.thresholding.policies import ThresholdValue, unweighted_shared_threshold


@given(
    st.lists(
        st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=12,
    )
)
def test_b1_shared_threshold_is_the_unweighted_mean_for_heterogeneous_inputs(values: list[float]) -> None:
    thresholds = tuple(ThresholdValue(value=value) for value in values)

    result = unweighted_shared_threshold(local_thresholds=thresholds)

    assert result.value == sum(values) / len(values)
