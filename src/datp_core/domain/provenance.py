"""Immutable provenance records and canonical value serialization."""

import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from math import isfinite
from pathlib import Path

from pydantic import BaseModel

from .enums import DatasetId, PopulationId, SerializationFormat, TrafficRateEvidenceType
from .values import ByteCount, Checksum, RowCount, checksum_text

type CanonicalValue = (
    None
    | bool
    | int
    | float
    | str
    | tuple["CanonicalValue", ...]
    | list["CanonicalValue"]
    | dict[str, "CanonicalValue"]
)


def canonical_value(value: object) -> CanonicalValue:
    """Convert a supported value into a deterministic, finite JSON document value."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical scientific provenance cannot contain non-finite floats")
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, BaseModel):
        return {name: canonical_value(getattr(value, name)) for name in type(value).model_fields}
    if is_dataclass(value) and not isinstance(value, type):
        own_fields = fields(value)
        if len(own_fields) == 1 and own_fields[0].name == "value":
            return canonical_value(getattr(value, own_fields[0].name))
        return {field.name: canonical_value(getattr(value, field.name)) for field in own_fields}
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return {key: canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return tuple(canonical_value(item) for item in value)
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    raise TypeError(f"unsupported canonical provenance value: {type(value).__qualname__}")


def canonical_mapping(value: object) -> dict[str, CanonicalValue]:
    """Return a canonical JSON object and reject non-mapping roots."""
    document = canonical_value(value)
    if not isinstance(document, dict):
        raise TypeError("canonical document root must be a mapping")
    return document


def canonical_checksum(value: object) -> Checksum:
    """Checksum one supported value under the canonical JSON contract."""
    payload = json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return checksum_text(payload)


@dataclass(frozen=True, slots=True)
class SourceFileProvenance:
    path: Path
    size_bytes: ByteCount
    checksum: Checksum
    row_count: RowCount


@dataclass(frozen=True, slots=True)
class DatasetProvenance:
    dataset: DatasetId
    sources: tuple[SourceFileProvenance, ...]
    schema_checksum: Checksum

    def __post_init__(self) -> None:
        if not isinstance(self.sources, tuple):
            raise TypeError("dataset sources must be an immutable tuple")


@dataclass(frozen=True, slots=True)
class CodeProvenance:
    revision: str
    dirty_state: bool

    def __post_init__(self) -> None:
        if not isinstance(self.revision, str) or not self.revision:
            raise ValueError("revision must be non-empty")
        if not isinstance(self.dirty_state, bool):
            raise TypeError("dirty state must be boolean")


@dataclass(frozen=True, slots=True)
class ProtocolProvenance:
    resolved_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True)
class CitationProvenance:
    citation_key: str
    source_title: str
    source_locator: str

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value for value in (self.citation_key, self.source_title, self.source_locator)
        ):
            raise ValueError("citation fields must be non-empty strings")


@dataclass(frozen=True, slots=True)
class TrafficRateProvenance:
    kind: TrafficRateEvidenceType
    source: str
    units: str
    applicable_population: PopulationId
    citation: CitationProvenance


@dataclass(frozen=True, slots=True)
class ArtifactProvenance:
    path: Path
    format: SerializationFormat
    checksum: Checksum
    schema_checksum: Checksum
