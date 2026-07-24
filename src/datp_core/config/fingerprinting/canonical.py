"""Configuration fingerprint calculation entry point.

Builds on the generic canonicalization primitives in ``core/hashing.py`` (``Fingerprint``,
``canonicalize_value``) to produce a fingerprint for a tagged configuration projection kind
(scientific or execution).
"""

from __future__ import annotations

from hashlib import blake2b
from json import dumps

from datp_core.core.hashing import Fingerprint, FingerprintPayload, canonicalize_value


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
