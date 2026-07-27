"""Source entry, inventory, and CSV validation models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.core.hashing import Checksum, compute_file_checksum, compute_payload_checksum
from datp_core.core.identifiers import DatasetId


class ConcreteSourceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_path: Path
    relative_path: Path
    source_tree_identifier: str


class ConcreteSourceInventory(BaseModel):
    model_config = ConfigDict(frozen=True)
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


class SourceRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_path: Path
    source_row_index: int
    values: tuple[float, ...]


class LabeledSourceRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_row: SourceRow
    label: str


class SourceRowFailure(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_path: Path
    source_row_index: int
    reason: str


class CsvValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    rows: tuple[SourceRow, ...]
    failures: tuple[SourceRowFailure, ...]


type SourceRowValidation = SourceRow | SourceRowFailure
type LabeledSourceRowValidation = LabeledSourceRow | SourceRowFailure
