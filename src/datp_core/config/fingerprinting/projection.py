"""Conversion of resolved domain records into primitive structures for canonical fingerprinting."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from types import MappingProxyType

import cattrs


def _build_projection_converter() -> cattrs.Converter:
    converter = cattrs.Converter()

    # MappingProxyType objects must be recursively converted to plain dicts
    # so the result is fully JSON-serializable.  A bare dict(mp) preserves
    # nested MappingProxyType values, so the hook walks the entire tree.
    def _unstructure_mappingproxy(mp: Mapping) -> dict:
        result: dict = {}
        for key, value in mp.items():
            if isinstance(value, MappingProxyType):
                result[key] = _unstructure_mappingproxy(value)
            elif isinstance(value, dict):
                result[key] = {
                    k: _unstructure_mappingproxy(v) if isinstance(v, MappingProxyType) else v for k, v in value.items()
                }
            else:
                result[key] = value
        return result

    converter.register_unstructure_hook(MappingProxyType, _unstructure_mappingproxy)

    return converter


@cache
def get_projection_converter() -> cattrs.Converter:
    return _build_projection_converter()


def unstructure_projection(value: object) -> object:
    """Convert resolved domain records into primitive structures for canonical fingerprinting."""
    return get_projection_converter().unstructure(value)
