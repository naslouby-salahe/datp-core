"""Domain value objects, constrained scalar wrappers, and typed registry implementation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PositiveInt:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError(f"Value must be a positive integer, got: {self.value}")

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class Seed:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value < 0:
            raise ValueError(f"Seed value must be non-negative integer, got: {self.value}")

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class PositiveFloat:
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or self.value <= 0.0:
            raise ValueError(f"Value must be a positive float, got: {self.value}")

    def __float__(self) -> float:
        return float(self.value)


@dataclass(frozen=True, slots=True)
class NonNegativeFloat:
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or self.value < 0.0:
            raise ValueError(f"Value must be non-negative float, got: {self.value}")

    def __float__(self) -> float:
        return float(self.value)


@dataclass(frozen=True, slots=True)
class Probability:
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or not (0.0 <= float(self.value) <= 1.0):
            raise ValueError(f"Probability must be in range [0.0, 1.0], got: {self.value}")

    def __float__(self) -> float:
        return float(self.value)


@dataclass(frozen=True, slots=True)
class RelativePath:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or self.value.startswith("/") or ".." in self.value:
            raise ValueError(f"RelativePath cannot be absolute or traverse parent directories: {self.value}")

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
