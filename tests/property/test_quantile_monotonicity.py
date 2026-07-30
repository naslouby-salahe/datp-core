import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.values import Quantile
from datp_core.thresholding.quantiles import exact_empirical_quantile

_SCORE = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)


@given(
    scores=st.lists(_SCORE, min_size=2, max_size=50),
    lower_quantile=st.floats(min_value=0.01, max_value=0.97, allow_nan=False),
    delta=st.floats(min_value=0.001, max_value=0.02, allow_nan=False),
)
def test_exact_empirical_quantile_is_monotone_nondecreasing_in_probability(
    scores: list[float], lower_quantile: float, delta: float
) -> None:
    array = np.asarray(scores, dtype=np.float64)
    upper_quantile = min(lower_quantile + delta, 0.99)
    lower = exact_empirical_quantile(array, Quantile(lower_quantile))
    upper = exact_empirical_quantile(array, Quantile(upper_quantile))
    assert lower.value <= upper.value + 1e-9


@given(scores=st.lists(_SCORE, min_size=1, max_size=50))
def test_exact_empirical_quantile_never_exceeds_the_maximum_score(scores: list[float]) -> None:
    array = np.asarray(scores, dtype=np.float64)
    result = exact_empirical_quantile(array, Quantile(0.999))
    assert result.value <= float(np.max(array)) + 1e-9


@given(scores=st.lists(_SCORE, min_size=1, max_size=50))
def test_exact_empirical_quantile_never_falls_below_the_minimum_score(scores: list[float]) -> None:
    array = np.asarray(scores, dtype=np.float64)
    result = exact_empirical_quantile(array, Quantile(0.001))
    assert result.value >= float(np.min(array)) - 1e-9
