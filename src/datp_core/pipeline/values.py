"""Domain value objects, constrained scalar wrappers, and typed registry implementation."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import cast

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


def validate_relative_path(instance: object, attribute: object, value: str) -> None:
    if not isinstance(value, str) or value.startswith("/") or ".." in value or not value.strip():
        raise ValueError(f"RelativePath must be a non-empty relative path without parent traversal: {value}")


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
class PositiveCount(PositiveInt):
    """Semantic wrapper for positive counts."""


@define(frozen=True, slots=True, order=True)
class Seed:
    value: int = field(validator=validate_non_negative_int, converter=require_int)

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
class LearningRate(PositiveFloat):
    """Semantic wrapper for training learning rates."""


@define(frozen=True, slots=True, order=True)
class ThresholdValue(NonNegativeFloat):
    """Semantic wrapper for decision threshold values."""


@define(frozen=True, slots=True, order=True)
class Probability:
    value: float = field(validator=validate_probability, converter=require_finite_real)

    def __float__(self) -> float:
        return float(self.value)


@define(frozen=True, slots=True, order=True)
class RelativePath:
    value: str = field(validator=validate_relative_path)

    def __str__(self) -> str:
        return self.value


class TypedDomainRegistry[K, V]:
    """Strict typed domain registry wrapping a mapping with immutable lookup contracts."""

    def __init__(self, _items: dict[K, V] | None = None) -> None:
        self._items: dict[K, V] = dict(_items) if _items is not None else {}

    def get(self, key: K) -> V:
        if key not in self._items:
            raise KeyError(f"Domain registry key not registered: {key}")
        return self._items[key]

    def contains(self, key: K) -> bool:
        return key in self._items

    def keys(self) -> tuple[K, ...]:
        return tuple(self._items.keys())

    def values(self) -> tuple[V, ...]:
        return tuple(self._items.values())

    def items(self) -> tuple[tuple[K, V], ...]:
        return tuple(self._items.items())

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key: K) -> V:
        return self.get(key)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __iter__(self) -> Iterator[K]:
        return iter(self._items.keys())


def deep_freeze(value: object) -> object:
    """Recursively convert authored dict/list structures into immutable Mapping/tuple equivalents."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(deep_freeze(item) for item in value)
    return value


type FrozenJson = str | int | float | bool | None | tuple["FrozenJson", ...] | Mapping[str, "FrozenJson"]
"""Immutable equivalent of an authored JsonValue tree for genuinely polymorphic authored contracts
(a field whose internal shape varies per experiment/policy/kind, where forcing a rigid record would
either be incorrect or require a dedicated record per authored instance). Deliberately not `Any` or a
mutable bag: it is a closed recursive union over exactly the JSON scalar/collection shapes, frozen."""


def freeze_json(value: object) -> FrozenJson:
    """Freeze an authored JsonValue-shaped structure for domain storage, preserving every field."""
    return cast("FrozenJson", deep_freeze(value))


def freeze_json_or_none(value: object | None) -> FrozenJson | None:
    return None if value is None else freeze_json(value)


def as_frozen_json_mapping(value: object) -> Mapping[str, FrozenJson]:
    return cast("Mapping[str, FrozenJson]", freeze_json(value))


def as_optional_frozen_json_mapping(value: object | None) -> Mapping[str, FrozenJson] | None:
    return None if value is None else as_frozen_json_mapping(value)


def as_str_mapping(value: object) -> Mapping[str, str]:
    return cast("Mapping[str, str]", deep_freeze(value))


def as_optional_str_mapping(value: object | None) -> Mapping[str, str] | None:
    return None if value is None else as_str_mapping(value)


def as_str_mapping_tuple(value: object) -> tuple[Mapping[str, str], ...]:
    return cast("tuple[Mapping[str, str], ...]", deep_freeze(list(cast("list[object]", value))))


def as_int_mapping(value: object) -> Mapping[str, int]:
    return cast("Mapping[str, int]", deep_freeze(value))


def as_optional_int_mapping(value: object | None) -> Mapping[str, int] | None:
    return None if value is None else as_int_mapping(value)
