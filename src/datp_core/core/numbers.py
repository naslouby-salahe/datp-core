"""Constrained scalar numeric value objects and their validation.

Single authority for positive/non-negative int and float validation and the one canonical
linear-interpolation quantile formula shared by threshold construction and metric dispersion
diagnostics.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from attrs import define, field


def validate_positive_int(instance: object, attribute: object, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"Value must be a positive integer, got: {value}")


def validate_non_negative_int(instance: object, attribute: object, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Value must be a non-negative integer, got: {value}")


def validate_positive_float(instance: object, attribute: object, value: float) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or float(value) <= 0.0
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"Value must be a finite positive float, got: {value}")


def validate_non_negative_float(instance: object, attribute: object, value: float) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or float(value) < 0.0
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"Value must be a finite non-negative float, got: {value}")


def validate_probability(instance: object, attribute: object, value: float) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not (0.0 <= float(value) <= 1.0)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"Probability must be a finite float in range [0.0, 1.0], got: {value}")


def require_int(value: int) -> int:
    """Accept only real integers; bool and strings are not scientific integers."""
    if type(value) is not int:
        raise TypeError(f"Expected an integer, got {type(value).__name__}")
    return value


def require_finite_real(value: float | int) -> float:
    """Accept real numeric literals without coercing strings or booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Expected a real number, got {type(value).__name__}")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"Expected a finite real number, got {value}")
    return converted


@define(frozen=True, slots=True, order=True)
class PositiveInt:
    value: int = field(validator=validate_positive_int, converter=require_int)

    def __int__(self) -> int:
        return self.value


@define(frozen=True, slots=True, order=True)
class PositiveFloat:
    value: float = field(validator=validate_positive_float, converter=require_finite_real)

    def __float__(self) -> float:
        return float(self.value)


@define(frozen=True, slots=True, order=True)
class NonNegativeFloat:
    value: float = field(validator=validate_non_negative_float, converter=require_finite_real)

    def __float__(self) -> float:
        return float(self.value)


@define(frozen=True, slots=True, order=True)
class Probability:
    value: float = field(validator=validate_probability, converter=require_finite_real)

    def __float__(self) -> float:
        return float(self.value)


def linear_quantile(values: Sequence[float], target_quantile: float) -> float:
    """Canonical linear-interpolation quantile, shared by every scientific consumer.

    Single source of truth for `method="linear"` quantile computation, so threshold
    construction and FPR-dispersion analysis cannot silently drift apart from each other.
    """
    return float(np.quantile(np.asarray(values, dtype=np.float64), target_quantile, method="linear"))
