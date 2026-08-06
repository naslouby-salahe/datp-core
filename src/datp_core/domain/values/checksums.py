"""Checksums and content identities."""

from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path

from datp_core.domain.values.base import _pydantic_value_schema


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


def checksum_text(payload: str) -> Checksum:
    return Checksum(sha256(payload.encode()).hexdigest())


def checksum_bytes(payload: bytes) -> Checksum:
    return Checksum(sha256(payload).hexdigest())


def checksum_file(path: Path) -> Checksum:
    with path.open("rb") as source:
        return Checksum(file_digest(source, "sha256").hexdigest())
