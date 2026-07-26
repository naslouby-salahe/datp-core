"""Seed value object and deterministic derived-seed construction."""

from __future__ import annotations

from hashlib import blake2b
from typing import Any

from attrs import define, field
from pydantic_core import core_schema

from datp_core.core.numbers import require_int, validate_non_negative_int


@define(frozen=True, slots=True, order=True)
class Seed:
    value: int = field(validator=validate_non_negative_int, converter=require_int)

    def __int__(self) -> int:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._pydantic_validate,
            serialization=core_schema.plain_serializer_function_ser_schema(lambda v: v.value),
        )

    @classmethod
    def _pydantic_validate(cls, v: object) -> Seed:
        if isinstance(v, cls):
            return v
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(f"Expected int for Seed, got {type(v).__name__}")
        return cls(v)


def derive_seed(key: str, digest_bytes: int, components: tuple[tuple[str, int | str], ...]) -> int:
    """Derive a deterministic seed from an ordered key and named, ascending-sorted components.

    Single canonical formula shared by every feature that derives a seed from a namespace key and
    named components (dataloader shuffling in learning/, partition retries in data/, calibration
    subsampling in thresholding/).
    """
    if not key or digest_bytes < 1:
        raise ValueError("Seed derivation requires a key and positive digest length")
    if tuple(name for name, _ in components) != tuple(sorted(name for name, _ in components)):
        raise ValueError("Seed derivation components must be ordered by ascending name")
    encoded = "|".join((key, *(f"{name}={value}" for name, value in components))).encode("utf-8")
    return int.from_bytes(blake2b(encoded, digest_size=digest_bytes).digest(), "big") % (2**32)
