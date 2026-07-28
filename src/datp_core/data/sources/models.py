"""Immutable source inventory and streaming-read records."""

from __future__ import annotations

from pathlib import Path

import msgspec
import pyarrow as pa

from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts.enums import SourceRole, SourceTreeKind
from datp_core.data.contracts.values import SourceTreeId


class SourceEntry(msgspec.Struct, frozen=True):
    source_path: Path
    relative_path: Path
    source_tree_id: SourceTreeId
    tree_kind: SourceTreeKind
    role: SourceRole


class SourceInventory(msgspec.Struct, frozen=True):
    dataset_id: DatasetId
    raw_data_root: Path
    entries: tuple[SourceEntry, ...]
    checksum: Checksum

    @property
    def file_count(self) -> int:
        return len(self.entries)

    @property
    def executable_entries(self) -> tuple[SourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.role is SourceRole.EXECUTABLE)


class CsvBatch(msgspec.Struct, frozen=True):
    record_batch: pa.RecordBatch


class CsvReadReport(msgspec.Struct, frozen=True):
    source_rows_seen: int
    valid_rows: int
    excluded_rows: int


class MutableCsvReadState:
    __slots__ = ("source_rows_seen", "valid_rows", "excluded_rows")

    def __init__(self) -> None:
        self.source_rows_seen = 0
        self.valid_rows = 0
        self.excluded_rows = 0

    def freeze(self) -> CsvReadReport:
        return CsvReadReport(
            source_rows_seen=self.source_rows_seen,
            valid_rows=self.valid_rows,
            excluded_rows=self.excluded_rows,
        )
