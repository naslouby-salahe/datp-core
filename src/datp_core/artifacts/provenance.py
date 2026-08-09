"""Checksums and deterministic content identities."""

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path

from datp_core.core.contracts import pydantic_value_schema

_ORDERED_TEXT_LENGTH_PREFIX_BYTES = 8


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)

    @classmethod
    def from_text(cls, payload: str) -> "Checksum":
        return cls(sha256(payload.encode()).hexdigest())

    @classmethod
    def from_bytes(cls, payload: bytes) -> "Checksum":
        return cls(sha256(payload).hexdigest())

    @classmethod
    def from_file(cls, path: Path) -> "Checksum":
        with path.open("rb") as source:
            return cls(file_digest(source, "sha256").hexdigest())

    @classmethod
    def from_ordered_texts(cls, values: Sequence[str]) -> "Checksum":
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
        return cls(digest.hexdigest())
