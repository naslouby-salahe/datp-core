"""Immutable provenance records and canonical scientific identity serialization."""

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, TypeAdapter

from .values.checksums import Checksum, checksum_text

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


type CanonicalValue = (
    None
    | bool
    | int
    | float
    | str
    | tuple["CanonicalValue", ...]
    | list["CanonicalValue"]
    | dict[str, "CanonicalValue"]
)

JSON_SEPARATORS = (",", ":")


def canonical_value(value: object) -> CanonicalValue:
    """Convert one supported scientific value into a deterministic finite JSON value."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical scientific identities cannot contain non-finite floats")
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, BaseModel):
        return {name: canonical_value(getattr(value, name)) for name in type(value).model_fields}
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_dataclass_value(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return {key: canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return tuple(canonical_value(item) for item in value)
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    raise TypeError(f"unsupported canonical scientific identity value: {type(value).__qualname__}")


def canonical_mapping(value: object) -> dict[str, CanonicalValue]:
    document = canonical_value(value)
    if not isinstance(document, dict):
        raise TypeError("canonical document root must be a mapping")
    return document


def canonical_json_text(value: object) -> str:
    """Serialize one supported value using the repository canonical identity contract."""
    return json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=JSON_SEPARATORS,
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_checksum(value: object) -> Checksum:
    return checksum_text(canonical_json_text(value))


def serialize_json_model(model: BaseModel, destination: Path) -> Checksum:
    """Persist one strict model through the repository canonical JSON contract."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_text(model)
    destination.write_text(payload, encoding="utf-8")
    return checksum_text(payload)


def _canonical_dataclass_value(value: "DataclassInstance") -> CanonicalValue:
    if getattr(type(value), "__get_pydantic_core_schema__", None) is not None:
        return canonical_value(TypeAdapter(type(value)).dump_python(value))
    own_fields = fields(value)
    if len(own_fields) == 1 and own_fields[0].name == "value":
        return canonical_value(getattr(value, own_fields[0].name))
    return {field.name: canonical_value(getattr(value, field.name)) for field in own_fields}
