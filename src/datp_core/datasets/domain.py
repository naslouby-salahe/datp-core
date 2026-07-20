"""Dataset readiness records retain evidence without modifying authored YAML."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from ..catalogue.domain import DatasetDefinition
from ..kernel.fingerprints import Fingerprint
from ..kernel.ids import DatasetId


class ReadinessStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFinding:
    code: str
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFileManifest:
    relative_path: str
    source_role: str
    byte_count: int
    checksum: Fingerprint
    header: tuple[str, ...]
    field_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaSummary:
    expected_field_count: int
    observed_headers: tuple[tuple[str, ...], ...]
    header_consistent: bool


class DatasetAdapter(Protocol):
    dataset_id: DatasetId

    def inspect(
        self, definition: DatasetDefinition, raw_root: Path, *, max_files: int | None = None
    ) -> DatasetReadinessReport: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetReadinessReport:
    dataset_id: DatasetId
    source_fingerprint: Fingerprint
    files: tuple[str, ...]
    findings: tuple[SourceFinding, ...]
    status: ReadinessStatus
    source_files: tuple[SourceFileManifest, ...] = ()
    schema: SchemaSummary | None = None
