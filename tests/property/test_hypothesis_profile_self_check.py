import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.property
@given(
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.integers(min_value=-1_000_000, max_value=1_000_000),
)
def test_integer_addition_is_commutative_within_profile_budget(left: int, right: int) -> None:
    assert left + right == right + left
