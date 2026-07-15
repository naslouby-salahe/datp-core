from dataclasses import FrozenInstanceError
from decimal import Decimal
from inspect import Parameter, signature
from typing import cast

import pytest

from datp_core.domain.data.partitioning import DirichletAlpha, DirichletAlphaSentinel
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ConfidenceLevel,
    CoverageRatio,
    EligibilityCoverage,
    FalsePositiveRate,
    Probability,
    TruePositiveRate,
)
from datp_core.domain.thresholding.policies import (
    DECIMAL_QUANTUM,
    FprTarget,
    ThresholdPercentile,
    ThresholdValue,
    validate_fpr_target,
)
from datp_core.domain.thresholding.variants import ConformalCoverage, ShrinkageWeight


def _set_attribute(instance: object, attribute_name: str, value: Decimal) -> None:
    setattr(instance, attribute_name, value)


@pytest.mark.parametrize(
    ("value_type", "value"),
    [
        (ThresholdPercentile, Decimal("0.9")),
        (FprTarget, Decimal("0.1")),
        (ConformalCoverage, Decimal("0")),
        (ConfidenceLevel, Decimal("0.95")),
        (CoverageRatio, Decimal("1")),
        (EligibilityCoverage, Decimal("0.5")),
        (Probability, Decimal("0.25")),
    ],
)
def test_decimal_value_objects_are_keyword_only_frozen_and_canonical(
    value_type: type[ThresholdPercentile]
    | type[FprTarget]
    | type[ConformalCoverage]
    | type[ConfidenceLevel]
    | type[CoverageRatio]
    | type[EligibilityCoverage]
    | type[Probability],
    value: Decimal,
) -> None:
    instance = value_type(value=value)

    assert instance.value == value.quantize(DECIMAL_QUANTUM)
    assert signature(value_type).parameters["value"].kind is Parameter.KEYWORD_ONLY
    replacement_value = Decimal("0.5")

    with pytest.raises(FrozenInstanceError):
        _set_attribute(instance, "value", replacement_value)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (Decimal("0.1234567890125"), Decimal("0.123456789012")),
        (Decimal("0.1234567890135"), Decimal("0.123456789014")),
    ],
)
def test_decimal_value_objects_use_twelve_place_half_even_rounding(source: Decimal, expected: Decimal) -> None:
    assert Probability(value=source).value == expected


@pytest.mark.parametrize(
    ("value_type", "invalid_value"),
    [
        (ThresholdPercentile, Decimal("0")),
        (FprTarget, Decimal("1")),
        (ConformalCoverage, Decimal("-0.1")),
        (ConfidenceLevel, Decimal("1")),
        (CoverageRatio, Decimal("1.1")),
        (EligibilityCoverage, Decimal("-0.1")),
        (Probability, Decimal("1.1")),
    ],
)
def test_decimal_value_objects_reject_out_of_range_values(
    value_type: type[ThresholdPercentile]
    | type[FprTarget]
    | type[ConformalCoverage]
    | type[ConfidenceLevel]
    | type[CoverageRatio]
    | type[EligibilityCoverage]
    | type[Probability],
    invalid_value: Decimal,
) -> None:
    with pytest.raises(DomainValidationError):
        value_type(value=invalid_value)


@pytest.mark.parametrize("nonfinite", [Decimal("NaN"), Decimal("Infinity")])
def test_decimal_value_objects_reject_nonfinite_values(nonfinite: Decimal) -> None:
    with pytest.raises(DomainValidationError):
        Probability(value=nonfinite)


def test_fpr_target_is_derived_from_and_checked_against_percentile() -> None:
    percentile = ThresholdPercentile(value=Decimal("0.9"))
    target = FprTarget.from_percentile(percentile=percentile)

    assert target.value == Decimal("0.100000000000")
    validate_fpr_target(percentile=percentile, target=target)
    invalid_target = FprTarget(value=Decimal("0.11"))

    with pytest.raises(DomainValidationError):
        validate_fpr_target(percentile=percentile, target=invalid_target)


def test_decimal_value_objects_reject_cross_value_object_construction() -> None:
    probability = Probability(value=Decimal("0.5"))
    # The constructor's static contract is correct; this deliberately supplies an invalid runtime object.
    runtime_value = cast(Decimal | float | int | str, probability)

    with pytest.raises(DomainValidationError):
        ConfidenceLevel(value=runtime_value)


@pytest.mark.parametrize(
    ("value_type", "accepted_value", "rejected_values"),
    [
        (ThresholdValue, 0.0, (-0.01, float("nan"), float("inf"), float("-inf"))),
        (ShrinkageWeight, 0.5, (1.01, float("nan"), float("inf"), float("-inf"))),
        (FalsePositiveRate, 0.1, (-0.01, float("nan"), float("inf"), float("-inf"))),
        (TruePositiveRate, 0.9, (1.01, float("nan"), float("inf"), float("-inf"))),
        (AuRocScore, 1.0, (-0.01, float("nan"), float("inf"), float("-inf"))),
    ],
)
def test_float_value_objects_enforce_finite_range_constraints(
    value_type: type[ThresholdValue]
    | type[ShrinkageWeight]
    | type[FalsePositiveRate]
    | type[TruePositiveRate]
    | type[AuRocScore],
    accepted_value: float,
    rejected_values: tuple[float, ...],
) -> None:
    assert value_type(value=accepted_value).value == accepted_value
    for rejected_value in rejected_values:
        with pytest.raises(DomainValidationError):
            value_type(value=rejected_value)


def test_float_value_objects_reject_cross_value_object_construction() -> None:
    rate = FalsePositiveRate(value=0.1)
    # The constructor's static contract is correct; this deliberately supplies an invalid runtime object.
    runtime_value = cast(float | int, rate)

    with pytest.raises(DomainValidationError):
        TruePositiveRate(value=runtime_value)


def test_dirichlet_alpha_accepts_only_positive_finite_values_or_iid() -> None:
    assert DirichletAlpha(value=1).value == 1.0
    assert DirichletAlpha(value=DirichletAlphaSentinel.IID).value is DirichletAlphaSentinel.IID

    for invalid_value in (0, -0.1, float("nan"), float("inf"), True):
        with pytest.raises(DomainValidationError):
            DirichletAlpha(value=invalid_value)

    # A raw string is intentionally distinct from the typed IID sentinel.
    raw_sentinel = cast(float | DirichletAlphaSentinel, "iid")
    with pytest.raises(DomainValidationError):
        DirichletAlpha(value=raw_sentinel)
