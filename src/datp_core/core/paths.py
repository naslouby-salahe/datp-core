"""Constrained path value objects.

Owns path-specific validation only. Filesystem authority and project-root resolution are
runtime/configuration responsibilities and must not be added here.
"""

from __future__ import annotations

from typing import Any

from attrs import define, field
from pydantic_core import core_schema


def validate_relative_path(instance: object, attribute: object, value: str) -> None:
    if not isinstance(value, str) or value.startswith("/") or ".." in value or not value.strip():
        raise ValueError(f"RelativePath must be a non-empty relative path without parent traversal: {value}")


@define(frozen=True, slots=True, order=True)
class RelativePath:
    value: str = field(validator=validate_relative_path)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._pydantic_validate,
            serialization=core_schema.plain_serializer_function_ser_schema(lambda v: v.value),
        )

    @classmethod
    def _pydantic_validate(cls, v: object) -> RelativePath:
        if isinstance(v, cls):
            return v
        if not isinstance(v, str):
            raise ValueError(f"Expected str for RelativePath, got {type(v).__name__}")
        return cls(v)
