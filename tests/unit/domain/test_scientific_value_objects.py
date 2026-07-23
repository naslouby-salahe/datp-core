"""Strict scientific scalar-value tests."""

import math

import pytest

from datp_core.pipeline.values import PositiveInt, Probability, Seed


@pytest.mark.parametrize("value", [True, "1", 1.0])
def test_positive_int_rejects_implicit_conversion(value: object) -> None:
    with pytest.raises(TypeError):
        PositiveInt(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, "1", math.inf, math.nan])
def test_probability_rejects_non_finite_and_implicit_conversion(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        Probability(value)  # type: ignore[arg-type]


def test_seed_rejects_bool() -> None:
    with pytest.raises(TypeError):
        Seed(True)
