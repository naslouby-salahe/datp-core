"""Immutable provenance records and canonical value serialization."""

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from functools import singledispatch
from math import isfinite
from pathlib import Path

from .enums import DatasetId, PopulationId, SerializationFormat, TrafficRateEvidenceType
from .values import ByteCount, Checksum, RowCount


@singledispatch
def canonical_value(value: object) -> object:
    """Convert a typed domain value into a deterministic JSON-serializable form."""
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: canonical_value(getattr(value, field.name)) for field in fields(value)}

    wrapped = getattr(value, "value", None)
    if wrapped is not None and wrapped is not value:
        return canonical_value(wrapped)

    raise TypeError(f"unsupported canonical provenance value: {type(value).__qualname__}")


@canonical_value.register(type(None))
@canonical_value.register(str)
@canonical_value.register(int)
def _(value: object) -> object:
    return value


@canonical_value.register(float)
def _(value: float) -> float:
    if not isfinite(value):
        raise ValueError("canonical scientific provenance cannot contain non-finite floats")
    return value


@canonical_value.register(Enum)
def _(value: Enum) -> object:
    return canonical_value(value.value)


@canonical_value.register(Mapping)
def _(value: Mapping) -> dict:
    return {str(key): canonical_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}


@canonical_value.register(tuple)
@canonical_value.register(list)
def _(value: tuple | list) -> list:
    return [canonical_value(item) for item in value]


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
