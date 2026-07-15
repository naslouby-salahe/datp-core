from decimal import Decimal
from math import isfinite
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ConfidenceLevel,
    FalsePositiveRate,
    Probability,
    TruePositiveRate,
)
from datp_core.domain.thresholding.policies import (
    FprTarget,
    ThresholdPercentile,
    ThresholdValue,
    validate_fpr_target,
)
from datp_core.domain.thresholding.variants import ShrinkageWeight


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_float_value_objects_handle_generated_finite_and_nonfinite_values(value: float) -> None:
    constructors = (
        (ThresholdValue, value >= 0),
        (ShrinkageWeight, 0 <= value <= 1),
        (FalsePositiveRate, 0 <= value <= 1),
        (TruePositiveRate, 0 <= value <= 1),
        (AuRocScore, 0 <= value <= 1),
    )

    for constructor, in_range in constructors:
        if isfinite(value) and in_range:
            assert constructor(value=value).value == value
        else:
            with pytest.raises(DomainValidationError):
                constructor(value=value)


@given(
    st.decimals(
        min_value=Decimal("0.000000000001"),
        max_value=Decimal("0.999999999999"),
        places=15,
    )
)
def test_probability_canonicalization_is_deterministic(value: Decimal) -> None:
    first = Probability(value=value)
    second = Probability(value=value)

    assert first == second
    assert first.value == second.value


@given(st.integers(min_value=1, max_value=999_999_999_999))
def test_fpr_target_matches_one_minus_canonical_percentile(numerator: int) -> None:
    percentile = ThresholdPercentile(value=Decimal(numerator) / Decimal("1000000000000"))
    direct_target = FprTarget(value=Decimal(1) - percentile.value)
    derived_target = FprTarget.from_percentile(percentile=percentile)

    validate_fpr_target(percentile=percentile, target=direct_target)
    validate_fpr_target(percentile=percentile, target=derived_target)
    assert direct_target == derived_target


@given(
    st.decimals(
        min_value=Decimal("0.000000000001"),
        max_value=Decimal("0.999999999999"),
        places=12,
    )
)
def test_probability_types_cannot_be_cross_constructed(value: Decimal) -> None:
    probability = Probability(value=value)
    # The constructor's static contract is correct; this deliberately supplies an invalid runtime object.
    runtime_value = cast(Decimal | float | int | str, probability)

    with pytest.raises(DomainValidationError):
        ConfidenceLevel(value=runtime_value)
