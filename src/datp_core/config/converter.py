"""Single cattrs conversion authority for config-to-domain and canonical projection.

Rules:
- One configured ``cattrs.Converter`` singleton.
- No global mutable registration outside this module.
- No per-call converter creation.
- No generic fallback that silently accepts unknown mappings.
- Used only when authored and domain shapes have the same meaning; semantic
  resolution remains explicit code elsewhere.

This converter deliberately does not add type-envelope hooks for value objects
or enums -- the canonical form of those types is handled by
``domain.fingerprints.canonicalize_value``, and the converter's job is only to
produce a nested dict/list structure from attrs records and MappingProxyType
instances.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

import cattrs

_PROJECTION_CONVERTER: cattrs.Converter | None = None


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


def get_projection_converter() -> cattrs.Converter:
    global _PROJECTION_CONVERTER
    if _PROJECTION_CONVERTER is None:
        _PROJECTION_CONVERTER = _build_projection_converter()
    return _PROJECTION_CONVERTER


def unstructure_projection(value: object) -> object:
    """Convert resolved domain records into primitive structures for canonical fingerprinting."""
    return get_projection_converter().unstructure(value)


def unstructure_mapping_proxy(mp: Mapping) -> dict:
    """Unstructure a MappingProxyType as a plain dict, for deterministic key ordering."""
    return dict(mp)
