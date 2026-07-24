"""Deep freezing and immutable projection helpers.

Recursively converts authored dict/list structures into immutable Mapping/tuple equivalents,
deterministically, so callers never repeat this conversion themselves.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import cast


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
