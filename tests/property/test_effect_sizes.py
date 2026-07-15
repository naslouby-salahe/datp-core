from math import isclose

from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.mathematics.effect_sizes import cliffs_delta

finite_samples = st.lists(
    st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), min_size=1, max_size=16
).map(tuple)


@given(finite_samples, finite_samples)
def test_cliffs_delta_is_antisymmetric_and_bounded(sample_a: tuple[float, ...], sample_b: tuple[float, ...]) -> None:
    delta = cliffs_delta(sample_a=sample_a, sample_b=sample_b)

    assert isclose(delta, -cliffs_delta(sample_a=sample_b, sample_b=sample_a))
    assert -1 <= delta <= 1


@given(finite_samples, finite_samples)
def test_cliffs_delta_matches_the_independent_tie_aware_pairwise_reference(
    sample_a: tuple[float, ...], sample_b: tuple[float, ...]
) -> None:
    favorable_a = sum(value_a > value_b for value_a in sample_a for value_b in sample_b)
    favorable_b = sum(value_a < value_b for value_a in sample_a for value_b in sample_b)
    expected = (favorable_a - favorable_b) / (len(sample_a) * len(sample_b))

    assert cliffs_delta(sample_a=sample_a, sample_b=sample_b) == expected
