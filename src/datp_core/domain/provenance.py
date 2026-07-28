"""Immutable provenance records."""

from dataclasses import dataclass
from pathlib import Path

from .enums import DatasetId, PopulationId, SerializationFormat, TrafficRateEvidenceType
from .values import ByteCount, Checksum


@dataclass(frozen=True, slots=True)
class SourceFileProvenance:
    path: Path
    size_bytes: ByteCount
    checksum: Checksum
    row_count: int

    def __post_init__(self) -> None:
        if isinstance(self.row_count, bool) or not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row count must be a non-negative integer")


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
