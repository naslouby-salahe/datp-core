"""Edge-IIoTset vocabulary fitting and normalization."""

from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path
from tempfile import TemporaryDirectory

from datp_core.data.adapters.edge_iiotset.models import (
    EdgeIIoTsetExternalIndexReport,
    EdgeIIoTsetNormalization,
    EdgeIIoTsetRow,
    EdgeIIoTsetVocabulary,
)
from datp_core.data.adapters.edge_iiotset.parsing import iter_edge_iiotset_source


def fit_edge_vocabulary(
    train_rows: tuple[EdgeIIoTsetRow, ...], categorical_headers: tuple[str, ...]
) -> EdgeIIoTsetVocabulary:
    if any(row.is_attack for row in train_rows):
        raise ValueError("Edge-IIoTset categorical vocabulary may only fit benign training rows")
    values: list[set[str]] = [set() for _ in categorical_headers]
    for row in train_rows:
        if len(row.categorical_values) != len(categorical_headers):
            raise ValueError("Edge-IIoTset categorical row width differs from configured schema")
        for index, value in enumerate(row.categorical_values):
            if value is not None:
                values[index].add(value)
    return EdgeIIoTsetVocabulary(
        categories_by_column=tuple(
            (header, tuple(sorted(values[index]))) for index, header in enumerate(categorical_headers)
        )
    )


def fit_edge_train_normalization(train_rows: tuple[EdgeIIoTsetRow, ...]) -> EdgeIIoTsetNormalization:
    if not train_rows or any(row.is_attack for row in train_rows):
        raise ValueError("Edge-IIoTset normalization requires non-empty benign training rows")
    width = len(train_rows[0].numeric_values)
    if any(len(row.numeric_values) != width for row in train_rows):
        raise ValueError("Edge-IIoTset numeric row width differs within training population")
    return EdgeIIoTsetNormalization(
        minimums=tuple(min(row.numeric_values[i] for row in train_rows) for i in range(width)),
        maximums=tuple(max(row.numeric_values[i] for row in train_rows) for i in range(width)),
    )


def index_edge_benign_sources(
    source_paths: tuple[Path, ...],
    normal_root: Path,
    attack_root: Path,
    numeric_headers: tuple[str, ...],
    categorical_headers: tuple[str, ...],
    binary_label_header: str,
    multiclass_label_header: str,
) -> EdgeIIoTsetExternalIndexReport:
    from datp_core.data.sources.models import SourceRowFailure

    seen = excluded = 0
    with TemporaryDirectory(prefix="datp_edge_index_") as temporary_directory:
        database = sqlite3.connect(Path(temporary_directory) / "edge.sqlite3")
        try:
            database.execute("PRAGMA journal_mode = OFF")
            database.execute(
                "CREATE TABLE canonical_rows (client_id TEXT, numeric_values TEXT, categorical_values TEXT, "
                "source_path TEXT, source_row_index INTEGER, "
                "PRIMARY KEY (client_id, numeric_values, categorical_values)) WITHOUT ROWID"
            )
            for path in sorted(source_paths):
                for result in iter_edge_iiotset_source(
                    path,
                    normal_root,
                    attack_root,
                    numeric_headers,
                    categorical_headers,
                    binary_label_header,
                    multiclass_label_header,
                ):
                    seen += 1
                    if isinstance(result, SourceRowFailure):
                        excluded += 1
                        continue
                    if result.is_attack or result.client_id is None:
                        continue
                    database.execute(
                        "INSERT OR IGNORE INTO canonical_rows VALUES (?, ?, ?, ?, ?)",
                        (
                            result.client_id,
                            struct.pack(f"!{len(result.numeric_values)}d", *result.numeric_values),
                            json.dumps(result.categorical_values, separators=(
                                ",", ":"), ensure_ascii=False),
                            result.source_path.as_posix(),
                            result.source_row_index,
                        ),
                    )
            canonical = int(database.execute("SELECT COUNT(*) FROM canonical_rows").fetchone()[0])
        finally:
            database.close()
    return EdgeIIoTsetExternalIndexReport(source_rows_seen=seen, excluded_rows=excluded, canonical_rows=canonical)
