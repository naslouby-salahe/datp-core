"""Checksums and deterministic content identities."""

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path

from datp_core.core.contracts import pydantic_value_schema

_ORDERED_TEXT_LENGTH_PREFIX_BYTES = 8


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


def checksum_text(payload: str) -> Checksum:#TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    return Checksum(sha256(payload.encode()).hexdigest())


def checksum_bytes(payload: bytes) -> Checksum: #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    return Checksum(sha256(payload).hexdigest())


def checksum_file(path: Path) -> Checksum:
    with path.open("rb") as source:
        return Checksum(file_digest(source, "sha256").hexdigest())


def ordered_text_checksum(values: Sequence[str]) -> Checksum: #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    digest = sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(
            len(encoded).to_bytes(
                _ORDERED_TEXT_LENGTH_PREFIX_BYTES,
                byteorder="big",
                signed=False,
            )
        )
        digest.update(encoded)
    return Checksum(digest.hexdigest())
