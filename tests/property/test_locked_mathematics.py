from decimal import Decimal
from math import fsum, sqrt

import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.mathematics.dispersion import ClientMoment, DefinedCvFpr, cv_fpr, pooled_variance
from datp_core.domain.mathematics.quantiles import fpr_target
from datp_core.domain.thresholding.policies import ThresholdPercentile


@given(
    st.lists(st.floats(min_value=0.001, max_value=1, allow_nan=False, allow_infinity=False), min_size=1, max_size=20)
)
def test_cv_fpr_matches_an_independent_population_reference(values: list[float]) -> None:
    mean_value = fsum(values) / len(values)
    expected = sqrt(fsum((value - mean_value) ** 2 for value in values) / len(values)) / mean_value
    outcome = cv_fpr(eligible_fprs=tuple(values))

    assert isinstance(outcome, DefinedCvFpr)
    assert outcome.value == pytest.approx(expected)


@given(
    st.integers(min_value=1, max_value=100),
    st.integers(min_value=1, max_value=100),
    st.floats(min_value=-100, max_value=-0.001, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.001, max_value=100, allow_nan=False, allow_infinity=False),
)
def test_pooled_variance_is_strictly_larger_than_within_only_when_means_differ(
    first_count: int,
    second_count: int,
    first_mean: float,
    second_mean: float,
) -> None:
    moments = (
        ClientMoment(sample_count=first_count, mean=first_mean, variance=1.0),
        ClientMoment(sample_count=second_count, mean=second_mean, variance=1.0),
    )
    within_only = 1.0

    assert pooled_variance(client_moments=moments) > within_only


@given(st.integers(min_value=1, max_value=999_999_999_999))
def test_fpr_target_is_exactly_one_minus_the_canonical_percentile(numerator: int) -> None:
    percentile = ThresholdPercentile(value=Decimal(numerator) / Decimal("1000000000000"))
    if Decimal(0) < percentile.value < Decimal(1):
        assert fpr_target(percentile=percentile).value == Decimal(1) - percentile.value
