"""Shared value-object comparison, arithmetic, and Pydantic-integration machinery."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import total_ordering
from math import isclose, isfinite
from types import NotImplementedType
from typing import ClassVar, cast

NUMERIC_ZERO: float = 0.0
NO_RELATIVE_TOLERANCE: float = 0.0


def floats_absolutely_close(left: float, right: float, absolute_tolerance: float) -> bool:
    """Compare floats with an explicit absolute tolerance and zero relative tolerance."""
    if absolute_tolerance < NUMERIC_ZERO:
        raise ValueError("absolute tolerance must be non-negative")
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance)


def floats_exactly_equal(left: float, right: float) -> bool:
    """Compare floats at full precision with no tolerance band."""
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=NUMERIC_ZERO)


def is_numeric_zero(value: float) -> bool:
    return floats_exactly_equal(value, NUMERIC_ZERO)


def _integer(value: int, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: int | float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


NumericValue = int | float


def _numeric_value(instance: object) -> NumericValue:
    value = getattr(instance, "value", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{type(instance).__name__} does not expose a numeric value")
    return value


def _compatible_value(self: object, other: object) -> NumericValue | NotImplementedType:
    if isinstance(other, (int, float)) and not isinstance(other, bool):
        return other
    if type(other) is type(self):
        return _numeric_value(other)
    family = getattr(self, "comparison_family", None)
    if family is not None and getattr(other, "comparison_family", None) == family:
        return _numeric_value(other)
    return NotImplemented


def _ordering_compare(self: object, other: object) -> bool | NotImplementedType:
    other_value = _compatible_value(self, other)
    if other_value is NotImplemented:
        return NotImplemented
    return _numeric_value(self) < other_value


def _typed_eq(self: object, other: object) -> bool | NotImplementedType:
    other_value = _compatible_value(self, other)
    if other_value is NotImplemented:
        return NotImplemented
    return _numeric_value(self) == other_value


def _add_impl[T: (PositiveIntegerValue, NonNegativeIntegerValue)](self: T, other: object) -> T | NotImplementedType:
    self_value = _numeric_value(self)
    if not isinstance(self_value, int):
        return NotImplemented
    constructor = cast(Callable[[int], T], type(self))
    if isinstance(other, int) and not isinstance(other, bool):
        return constructor(self_value + other)
    if type(other) is type(self):
        other_value = _numeric_value(other)
        return constructor(self_value + int(other_value))
    return NotImplemented


def _radd_impl[T: (PositiveIntegerValue, NonNegativeIntegerValue)](self: T, other: object) -> T | NotImplementedType:
    self_value = _numeric_value(self)
    if isinstance(self_value, int) and isinstance(other, int) and not isinstance(other, bool):
        constructor = cast(Callable[[int], T], type(self))
        return constructor(other + self_value)
    return NotImplemented


def _coerce_instance(cls, value):
    return value if isinstance(value, cls) else cls(value)


def _pydantic_value_schema(cls, _source_type, _handler):
    """Validate a raw scalar into a value object and serialize its scalar value."""
    from pydantic_core import core_schema as _cs

    return _cs.no_info_plain_validator_function(
        lambda value: _coerce_instance(cls, value),
        serialization=_cs.plain_serializer_function_ser_schema(lambda instance: instance.value),
    )


def _str_enum_schema(cls, _source_type, _handler):
    """Validate a raw string into a StrEnum member."""
    from pydantic_core import core_schema as _cs

    def _validate(value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"expected {cls.__name__} or str")
        return cls(value)

    return _cs.no_info_plain_validator_function(_validate)


def _str_subclass_schema(cls, _source_type, _handler):
    from pydantic_core import core_schema as _cs

    return _cs.no_info_plain_validator_function(
        lambda value: _coerce_instance(cls, value),
        serialization=_cs.plain_serializer_function_ser_schema(str),
    )


@total_ordering
@dataclass(frozen=True, slots=True)
class PositiveIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"
    comparison_family: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 1)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    __add__ = _add_impl
    __radd__ = _radd_impl
    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class NonNegativeIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"
    comparison_family: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 0)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    __add__ = _add_impl
    __radd__ = _radd_impl
    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class FiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"
    comparison_family: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _number(self.value, self.validation_name))

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    def __float__(self) -> float:
        return self.value

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


class PositiveFiniteFloatValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value <= 0:
            raise ValueError(f"{self.validation_name} must be positive")


class NonNegativeFiniteFloatValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value < 0:
            raise ValueError(f"{self.validation_name} must be non-negative")


class OpenUnitIntervalValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 < self.value < 1:
            raise ValueError(f"{self.validation_name} must be in (0, 1)")


class ClosedUnitIntervalValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 <= self.value <= 1:
            raise ValueError(f"{self.validation_name} must be in [0, 1]")


class _NonEmptyString(str):
    validation_name: ClassVar[str] = "value"

    def __new__(cls, value: str):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{cls.validation_name} must be a non-empty string")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


def _validate_non_empty_tuple(values: tuple, field_name: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field_name} requires a non-empty tuple")


def _validate_unique(values: tuple, field_name: str) -> None:
    if len(frozenset(values)) != len(values):
        raise ValueError(f"{field_name} must be unique")


def _sequence_pydantic_schema(cls, _source_type, _handler):
    from pydantic_core import core_schema as _cs

    def _validate(value):
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            return cls(tuple(value))
        raise ValueError(f"expected sequence, got {type(value)}")

    return _cs.no_info_plain_validator_function(
        _validate,
        serialization=_cs.plain_serializer_function_ser_schema(list),
    )
