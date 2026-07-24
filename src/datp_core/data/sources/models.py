"""Source entry, inventory, and CSV validation models."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.core.hashing import Checksum, compute_file_checksum, compute_payload_checksum
from datp_core.core.identifiers import DatasetId


@define(frozen=True, slots=True, kw_only=True)
class ConcreteSourceEntry:
    source_path: Path
    relative_path: Path
    source_tree_identifier: str


@define(frozen=True, slots=True, kw_only=True)
class ConcreteSourceInventory:
    dataset_id: DatasetId
    entries: tuple[ConcreteSourceEntry, ...]

    @property
    def file_count(self) -> int:
        return len(self.entries)

    def fingerprint(self) -> Checksum:
        payload = "\n".join(
            f"{entry.relative_path.as_posix()}:{compute_file_checksum(entry.source_path).value}"
            for entry in self.entries
        ).encode("utf-8")
        return compute_payload_checksum(payload)


@define(frozen=True, slots=True, kw_only=True)
class SourceRow:
    source_path: Path
    source_row_index: int
    values: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class LabeledSourceRow:
    source_row: SourceRow
    label: str


@define(frozen=True, slots=True, kw_only=True)
class SourceRowFailure:
    source_path: Path
    source_row_index: int
    reason: str


@define(frozen=True, slots=True, kw_only=True)
class CsvValidationResult:
    rows: tuple[SourceRow, ...]
    failures: tuple[SourceRowFailure, ...]


type SourceRowValidation = SourceRow | SourceRowFailure
type LabeledSourceRowValidation = LabeledSourceRow | SourceRowFailure
