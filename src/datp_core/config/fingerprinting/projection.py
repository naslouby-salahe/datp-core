"""Conversion of resolved domain records into primitive structures for canonical fingerprinting."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel


def _unstructure_value(value: object) -> object:
    """Recursively convert any Mapping within primitive containers."""
    if isinstance(value, BaseModel):
        return _unstructure_value(value.model_dump(mode="python"))
    if isinstance(value, Mapping):
        return {k: _unstructure_value(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [_unstructure_value(item) for item in value]
    return value


def unstructure_projection(value: object) -> object:
    """Convert resolved domain records into primitive structures for canonical fingerprinting."""
    if isinstance(value, BaseModel):
        return _unstructure_value(value.model_dump(mode="python"))
    if isinstance(value, Mapping):
        return _unstructure_value(dict(value))
    if isinstance(value, tuple | list):
        return [_unstructure_value(item) for item in value]
    return value
