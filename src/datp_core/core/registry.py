"""Typed immutable domain registry.

Wraps a mapping with deterministic iteration, typed lookup, and clear missing-key errors, without
exposing mutable internals.
"""

from __future__ import annotations

from collections.abc import Iterator


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
