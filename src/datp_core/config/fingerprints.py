"""Configuration-specific fingerprint entry points and the cattrs projection converter.

Builds on the generic hashing/canonicalization primitives in ``pipeline.fingerprints``
(``Fingerprint``, ``canonicalize_value``) to produce the two fingerprint kinds the resolution
flow ends with: the scientific fingerprint and the execution fingerprint.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from hashlib import blake2b
from json import dumps
from types import MappingProxyType

import cattrs

from datp_core.core.hashing import Fingerprint, FingerprintPayload, canonicalize_value


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


def compute_fingerprint(kind: str, projection: object) -> Fingerprint:
    """Compute canonical 256-bit BLAKE2b fingerprint for a configuration projection."""
    envelope = FingerprintPayload(
        schema_version=1,
        kind=kind,
        payload=canonicalize_value(projection),
    )
    json_bytes = dumps(
        envelope._asdict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    hex_digest = blake2b(json_bytes, digest_size=32).hexdigest()
    return Fingerprint(value=hex_digest)
