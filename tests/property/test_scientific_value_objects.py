import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.values import Ratio


@given(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False))
def test_ratio_accepts_bounded_values(value: float) -> None:
    assert Ratio(value).value == value


@given(
    st.one_of(
        st.floats(max_value=-0.000001, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.000001, allow_nan=False, allow_infinity=False),
    )
)
def test_ratio_rejects_out_of_domain_values(value: float) -> None:
    with pytest.raises(ValueError):
        Ratio(value)
