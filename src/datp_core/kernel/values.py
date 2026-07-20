"""Small validated value objects and the generic immutable registry."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Protocol, TypeVar, runtime_checkable

from .errors import RegistryError

type ScalarValue = str | int | float | bool | None
"""A scalar that can be represented in a resolved scientific definition."""

type StructuredValue = ScalarValue | tuple[StructuredValue, ...] | Mapping[str, StructuredValue]
"""An immutable, recursively structured configuration value.

Resolved catalogue records expose this type rather than an unbounded ``object``
bag. Lists from authored YAML are converted to tuples and mappings are copied
into mapping proxies at the configuration boundary.
"""


@dataclass(frozen=True, slots=True, order=True)
class Probability:
    value: float

    def __post_init__(self) -> None:
        if not isfinite(self.value) or not 0.0 <= self.value <= 1.0:
            raise ValueError("probability must be finite and in [0, 1]")


@dataclass(frozen=True, slots=True, order=True)
class PositiveFloat:
    value: float

    def __post_init__(self) -> None:
        if not isfinite(self.value) or self.value <= 0.0:
            raise ValueError("value must be a finite positive float")


@dataclass(frozen=True, slots=True, order=True)
class NonNegativeFloat:
    value: float

    def __post_init__(self) -> None:
        if not isfinite(self.value) or self.value < 0.0:
            raise ValueError("value must be a finite non-negative float")


@dataclass(frozen=True, slots=True, order=True)
class PositiveInt:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("value must be positive")


@dataclass(frozen=True, slots=True, order=True)
class Seed:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("seed must be non-negative")


@dataclass(frozen=True, slots=True, order=True)
class RoundNumber:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("round must be positive")


@dataclass(frozen=True, slots=True)
class Formula:
    expression: str

    def __post_init__(self) -> None:
        if not self.expression.strip():
            raise ValueError("formula must not be blank")


@dataclass(frozen=True, slots=True)
class InterpretationRule:
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("interpretation rule must not be blank")


@dataclass(frozen=True, slots=True)
class RelativePath:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value.startswith("/") or ".." in self.value.split("/"):
            raise ValueError("path must be a non-empty relative path without traversal")


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@runtime_checkable
class _Identified(Protocol):
    @property
    def identifier(self) -> Hashable: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class FrozenRegistry[K: Hashable, V]:
    _items: Mapping[K, V]

    def __post_init__(self) -> None:
        copied = dict(self._items)
        for key, definition in copied.items():
            definition_identifier: Hashable = definition.identifier if isinstance(definition, _Identified) else key
            if definition_identifier != key:
                raise RegistryError(f"registry key {key!s} does not match definition identifier")
        object.__setattr__(self, "_items", MappingProxyType(copied))

    def get(self, key: K) -> V:
        return self._items[key]

    def ordered(self) -> tuple[V, ...]:
        return tuple(self._items[key] for key in sorted(self._items, key=str))

    def items(self) -> tuple[tuple[K, V], ...]:
        return tuple((key, self._items[key]) for key in sorted(self._items, key=str))

    def contains(self, key: K) -> bool:
        return key in self._items

    def __len__(self) -> int:
        return len(self._items)
