"""Canonical hashing and value-canonicalization primitives shared by configuration, artifacts, and datasets.

Configuration-specific fingerprint entry points (compute_scientific_fingerprint,
compute_execution_fingerprint) live in configuration/fingerprints.py, which builds on these primitives.
"""

from __future__ import annotations

import math
from enum import Enum
from hashlib import blake2b
from pathlib import Path
from typing import NamedTuple

from attrs import define, field

from datp_core.pipeline.identifiers import _DomainIdentifier
from datp_core.pipeline.values import NonNegativeFloat, PositiveFloat, PositiveInt, Probability, RelativePath, Seed

type CanonicalProjection = str | int | bool | None | list[CanonicalProjection] | dict[str, CanonicalProjection]


def validate_hex64(instance: object, attribute: object, value: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or not all(c in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(f"Value must be a 64-character hexadecimal digest, got: {value}")


@define(frozen=True, slots=True, order=True)
class Fingerprint:
    value: str = field(validator=validate_hex64)

    def __str__(self) -> str:
        return self.value


@define(frozen=True, slots=True, order=True)
class Checksum:
    value: str = field(validator=validate_hex64)

    def __str__(self) -> str:
        return self.value


class FingerprintPayload(NamedTuple):
    schema_version: int
    kind: str
    payload: CanonicalProjection


def canonicalize_value(obj: object) -> CanonicalProjection:
    if isinstance(
        obj,
        (
            Checksum,
            Fingerprint,
            NonNegativeFloat,
            PositiveFloat,
            PositiveInt,
            Probability,
            RelativePath,
            Seed,
            _DomainIdentifier,
        ),
    ):
        return {"type": f"{type(obj).__module__}.{type(obj).__qualname__}", "value": str(obj.value)}
    if isinstance(obj, Enum):
        return {"enum": f"{type(obj).__module__}.{type(obj).__qualname__}", "value": str(obj.value)}
    if isinstance(obj, dict):
        if not all(isinstance(key, str) for key in obj):
            raise TypeError("Fingerprint mappings must use string keys")
        return {key: canonicalize_value(value) for key, value in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [canonicalize_value(item) for item in obj]
    if isinstance(obj, set):
        return [canonicalize_value(item) for item in sorted(obj, key=str)]
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float values cannot be fingerprinted: {obj}")
        return format(obj, ".17g")
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    raise TypeError(f"Unsupported value in fingerprint projection: {type(obj).__name__}")


def compute_payload_checksum(payload: bytes) -> Checksum:
    """Compute BLAKE2b checksum (256-bit / 64 hex characters) of raw byte payload."""
    hex_digest = blake2b(payload, digest_size=32).hexdigest()
    return Checksum(value=hex_digest)


def compute_file_checksum(path: Path, chunk_size: int = 1_048_576) -> Checksum:
    """Compute a BLAKE2b payload checksum without loading an artifact file into memory."""
    if chunk_size <= 0:
        raise ValueError("Checksum chunk size must be positive")
    digest = blake2b(digest_size=32)
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return Checksum(value=digest.hexdigest())
