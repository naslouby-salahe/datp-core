"""Constrained path value objects.

Owns path-specific validation only. Filesystem authority and project-root resolution are
runtime/configuration responsibilities and must not be added here.
"""

from __future__ import annotations

from attrs import define, field


def validate_relative_path(instance: object, attribute: object, value: str) -> None:
    if not isinstance(value, str) or value.startswith("/") or ".." in value or not value.strip():
        raise ValueError(
            f"RelativePath must be a non-empty relative path without parent traversal: {value}")


@define(frozen=True, slots=True, order=True)
class RelativePath:
    value: str = field(validator=validate_relative_path)

    def __str__(self) -> str:
        return self.value
