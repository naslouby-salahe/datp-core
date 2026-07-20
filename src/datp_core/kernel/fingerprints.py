"""Canonical scientific fingerprinting with no filesystem-dependent identity."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import blake2b
from json import dumps

from .values import StructuredValue


@dataclass(frozen=True, slots=True)
class Fingerprint:
    algorithm: str
    hexadecimal: str


def _normalise(value: StructuredValue) -> StructuredValue:
    if isinstance(value, Mapping):
        return {key: _normalise(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return tuple(_normalise(item) for item in value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite values cannot be fingerprinted")
        return format(value, ".17g")
    return value


def fingerprint(value: StructuredValue) -> Fingerprint:
    encoded = dumps(_normalise(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return Fingerprint(algorithm="blake2b-256", hexadecimal=blake2b(encoded, digest_size=32).hexdigest())
