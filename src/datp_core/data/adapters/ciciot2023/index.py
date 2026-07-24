"""CICIoT2023 SQLite index for deduplication and streaming Parquet output."""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.data.adapters.ciciot2023.identity import materialize_ciciot2023_merged_source_row
from datp_core.data.adapters.ciciot2023.models import CICIoT2023MaterializationReport
from datp_core.data.contracts.materialization import DatasetMaterialization
from datp_core.data.sources.csv import iter_labeled_numeric_csv_source
from datp_core.data.sources.models import SourceRowFailure


def write_ciciot2023_materialized_parquet(
    source_paths: tuple[Path, ...],
    target_path: Path,
    feature_headers: tuple[str, ...],
    label_header: str,
    merged_root: Path,
    benign_label: str,
    materialization: DatasetMaterialization,
    batch_size: int,
) -> CICIoT2023MaterializationReport:
    import math

    from datp_core.data.contracts.enums import SplitMethod

    if not source_paths or batch_size <= 0:
        raise ValueError("CICIoT2023 materialization requires source files and a positive Parquet batch size")
    if materialization.split_method != SplitMethod.RANDOM_FRACTIONAL or materialization.split_seed is None:
        raise ValueError("CICIoT2023 materialization requires configured random_fractional split and seed")
    train_ratio = float(materialization.ratio("train"))
    calibration_ratio = float(materialization.ratio("calibration"))
    test_ratio = float(materialization.ratio("test"))
    if not math.isclose(train_ratio + calibration_ratio + test_ratio, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("CICIoT2023 random split ratios must sum exactly to one")
    source_rows_seen = 0
    excluded_rows = 0
    with TemporaryDirectory(prefix="datp_ciciot2023_") as temporary_directory:
        database = sqlite3.connect(Path(temporary_directory) / "equivalence.sqlite3")
        try:
            database.execute("PRAGMA journal_mode = OFF")
            database.execute("PRAGMA synchronous = OFF")
            database.execute(
                """CREATE TABLE canonical_rows (
                    is_attack INTEGER NOT NULL, features BLOB NOT NULL, source_path TEXT NOT NULL,
                    source_row_index INTEGER NOT NULL, multiclass_label TEXT NOT NULL,
                    class_digest BLOB NOT NULL, split TEXT, PRIMARY KEY (is_attack, features)
                ) WITHOUT ROWID"""
            )
            for source_path in sorted(source_paths):
                for result in iter_labeled_numeric_csv_source(source_path, feature_headers, label_header):
                    source_rows_seen += 1
                    if isinstance(result, SourceRowFailure):
                        excluded_rows += 1
                        continue
                    row = materialize_ciciot2023_merged_source_row(result, merged_root, benign_label)
                    feature_blob = _serialize_features(row.source_row.values)
                    database.execute(
                        """INSERT OR IGNORE INTO canonical_rows
                        (is_attack, features, source_path, source_row_index, multiclass_label, class_digest)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            int(row.identity.is_attack),
                            feature_blob,
                            row.identity.source_path.as_posix(),
                            row.identity.source_row_index,
                            row.multiclass_label,
                            bytes.fromhex(_equivalence_hash_bytes((row.source_row.values, row.identity.is_attack))),
                        ),
                    )
            canonical_rows = int(database.execute("SELECT COUNT(*) FROM canonical_rows").fetchone()[0])
            conflicting_groups = int(
                database.execute(
                    "SELECT COUNT(*) FROM (SELECT features FROM canonical_rows "
                    "GROUP BY features HAVING COUNT(DISTINCT is_attack) > 1)"
                ).fetchone()[0]
            )
            database.execute("UPDATE canonical_rows SET split = 'test' WHERE is_attack = 1")
            from random import Random

            generator = Random(materialization.split_seed.value)
            for is_attack, features in database.execute(
                "SELECT is_attack, features FROM canonical_rows WHERE is_attack = 0 ORDER BY class_digest"
            ):
                draw = generator.random()
                role = (
                    "train"
                    if draw < train_ratio
                    else "calibration"
                    if draw < train_ratio + calibration_ratio
                    else "test"
                )
                database.execute(
                    "UPDATE canonical_rows SET split = ? WHERE is_attack = ? AND features = ?",
                    (role, is_attack, features),
                )
            database.commit()
            written_rows = _write_ciciot_parquet_from_index(database, target_path, feature_headers, batch_size)
        finally:
            database.close()
    return CICIoT2023MaterializationReport(
        source_rows_seen=source_rows_seen,
        excluded_rows=excluded_rows,
        canonical_rows=canonical_rows,
        duplicate_rows_removed=source_rows_seen - excluded_rows - canonical_rows,
        conflicting_label_feature_group_count=conflicting_groups,
        written_rows=written_rows,
    )


def _write_ciciot_parquet_from_index(
    database: sqlite3.Connection, target_path: Path, feature_headers: tuple[str, ...], batch_size: int
) -> int:
    schema = pa.schema(
        [
            ("split", pa.string()),
            ("client_id", pa.string()),
            ("is_attack", pa.bool_()),
            ("multiclass_label", pa.string()),
            ("source_path", pa.string()),
            ("source_row_index", pa.int64()),
            *((header, pa.float64()) for header in feature_headers),
        ]
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    records: dict[str, list[object]] = {field.name: [] for field in schema}
    written_rows = 0
    with pq.ParquetWriter(target_path, schema, compression="zstd", use_dictionary=False) as writer:
        for split, is_attack, features, source_path, source_row_index, multiclass_label in database.execute(
            "SELECT split, is_attack, features, source_path, source_row_index, multiclass_label FROM canonical_rows "
            "ORDER BY CASE split WHEN 'train' THEN 0 WHEN 'calibration' THEN 1 ELSE 2 END, "
            "source_path, source_row_index"
        ):
            records["split"].append(split)
            records["client_id"].append(Path(source_path).name)
            records["is_attack"].append(bool(is_attack))
            records["multiclass_label"].append(multiclass_label)
            records["source_path"].append(source_path)
            records["source_row_index"].append(source_row_index)
            for header, value in zip(
                feature_headers, _deserialize_features(features, len(feature_headers)), strict=True
            ):
                records[header].append(value)
            if len(records["split"]) == batch_size:
                writer.write_table(pa.table(records, schema=schema))
                written_rows += len(records["split"])
                records = {field.name: [] for field in schema}
        if records["split"]:
            writer.write_table(pa.table(records, schema=schema))
            written_rows += len(records["split"])
    return written_rows


def _serialize_features(values: tuple[float, ...]) -> bytes:
    return struct.pack(f"!{len(values)}d", *values)


def _deserialize_features(payload: bytes, feature_count: int) -> tuple[float, ...]:
    if len(payload) != feature_count * 8:
        raise ValueError("CICIoT2023 equivalence index has an invalid feature payload width")
    return struct.unpack(f"!{feature_count}d", payload)


def _equivalence_hash_bytes(equivalence_key: tuple[tuple[float, ...], bool]) -> str:
    import hashlib

    feature_values, is_attack = equivalence_key
    digest = hashlib.blake2b(digest_size=32)
    digest.update(bytes((is_attack,)))
    digest.update(_serialize_features(feature_values))
    return digest.hexdigest()
