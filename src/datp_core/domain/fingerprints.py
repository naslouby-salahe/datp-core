"""Canonical scientific fingerprinting via hashlib BLAKE2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import blake2b
from json import dumps
from typing import Any


@dataclass(frozen=True, slots=True, order=True)
class Fingerprint:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) != 64:
            raise ValueError("Fingerprint value must be a 64-character hex digest")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) != 64:
            raise ValueError("Checksum value must be a 64-character hex digest")

    def __str__(self) -> str:
        return self.value


def _normalize_obj(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _normalize_obj(v) for k, v in sorted(obj.items(), key=lambda x: str(x[0]))}
    if isinstance(obj, (list, tuple)):
        return [_normalize_obj(item) for item in obj]
    if isinstance(obj, set):
        return [_normalize_obj(item) for item in sorted(obj, key=str)]
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            raise ValueError("non-finite values cannot be fingerprinted")
        return format(obj, ".17g")
    if hasattr(obj, "value"):
        return _normalize_obj(obj.value)
    return obj


def compute_fingerprint(data: Any) -> Fingerprint:
    """Compute canonical BLAKE2b fingerprint (256-bit / 64 hex characters) of a data structure."""
    normalized = _normalize_obj(data)
    json_bytes = dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    hex_digest = blake2b(json_bytes, digest_size=32).hexdigest()
    return Fingerprint(value=hex_digest)


def compute_payload_checksum(payload: bytes) -> Checksum:
    """Compute BLAKE2b checksum (256-bit / 64 hex characters) of raw byte payload."""
    hex_digest = blake2b(payload, digest_size=32).hexdigest()
    return Checksum(value=hex_digest)
