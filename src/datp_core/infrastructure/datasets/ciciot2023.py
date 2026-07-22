"""CICIoT2023 merged-source identity and binary-label materialization rules."""

from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq
from attrs import define

from datp_core.application.ports import SourceInventory
from datp_core.domain.catalogue import SweepConditionRecord
from datp_core.domain.datasets import (
    AdapterKind,
    DatasetMaterialization,
    DatasetSetup,
    PartitionSeedContract,
    ResolvedDataset,
)
from datp_core.infrastructure.datasets.csv_source import (
    LabeledSourceRow,
    SourceRow,
    SourceRowFailure,
    iter_labeled_numeric_csv_source,
)
from datp_core.infrastructure.tables.parquet_io import normalize_materialized_parquet


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023RowIdentity:
    """Configured file pseudo-client and label semantics for one merged CSV row."""

    client_id: str
    is_attack: bool
    source_path: Path
    source_row_index: int


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023MaterializedRow:
    """One validated merged-source row before global equivalence-class deduplication."""

    identity: CICIoT2023RowIdentity
    multiclass_label: str
    source_row: SourceRow


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023DeduplicationResult:
    """Canonical global rows and audit counts required by the authored exclusion policy."""

    canonical_rows: tuple[CICIoT2023MaterializedRow, ...]
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023SplitRows:
    """Configured random split where attack rows are evaluation-only."""

    train: tuple[CICIoT2023MaterializedRow, ...]
    calibration: tuple[CICIoT2023MaterializedRow, ...]
    test: tuple[CICIoT2023MaterializedRow, ...]
    deduplication: CICIoT2023DeduplicationResult


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023MaterializationReport:
    """Bounded merged-source materialization counts, including explicit exclusions."""

    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int
    written_rows: int


def materialize_ciciot2023_merged_identity(
    source_path: Path,
    source_row_index: int,
    merged_root: Path,
    label: str,
    benign_label: str,
) -> CICIoT2023RowIdentity:
    """Derive the configured pseudo-client and binary label without row-position joins."""
    try:
        source_path.relative_to(merged_root)
    except ValueError as exc:
        raise ValueError("CICIoT2023 merged source path escapes the configured merged root") from exc
    if source_row_index < 1:
        raise ValueError("CICIoT2023 source row index must be one-based and positive")
    normalized_label = label.strip()
    if not normalized_label:
        raise ValueError("CICIoT2023 merged source label cannot be blank")
    return CICIoT2023RowIdentity(
        client_id=source_path.name,
        is_attack=normalized_label.upper() != benign_label.upper(),
        source_path=source_path,
        source_row_index=source_row_index,
    )


def materialize_ciciot2023_merged_source_row(
    row: LabeledSourceRow, merged_root: Path, benign_label: str
) -> CICIoT2023MaterializedRow:
    """Turn one validated merged CSV row into typed CICIoT2023 provenance and label data."""
    return CICIoT2023MaterializedRow(
        identity=materialize_ciciot2023_merged_identity(
            source_path=row.source_row.source_path,
            source_row_index=row.source_row.source_row_index,
            merged_root=merged_root,
            label=row.label,
            benign_label=benign_label,
        ),
        multiclass_label=row.label,
        source_row=row.source_row,
    )


def canonicalize_and_split_ciciot2023_rows(
    rows: tuple[CICIoT2023MaterializedRow, ...], materialization: DatasetMaterialization
) -> CICIoT2023SplitRows:
    """Apply global exact duplicate handling and seeded class-level CICIoT2023 splitting."""
    if materialization.split_method != "random_fractional":
        raise ValueError("CICIoT2023 materialization requires the configured random_fractional split")
    if materialization.split_seed is None:
        raise ValueError("CICIoT2023 random split requires an explicit configured split seed")
    train_ratio = float(materialization.ratio("train"))
    calibration_ratio = float(materialization.ratio("calibration"))
    test_ratio = float(materialization.ratio("test"))
    if not math.isclose(train_ratio + calibration_ratio + test_ratio, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("CICIoT2023 random split ratios must sum exactly to one")

    ordered_rows = tuple(sorted(rows, key=_provenance_key))
    equivalence_classes: dict[tuple[tuple[float, ...], bool], list[CICIoT2023MaterializedRow]] = {}
    labels_by_feature_hash: dict[str, set[bool]] = {}
    for row in ordered_rows:
        if not all(math.isfinite(value) for value in row.source_row.values):
            raise ValueError("CICIoT2023 source rows must contain only finite numeric model features")
        feature_hash = _feature_hash(row.source_row.values)
        labels_by_feature_hash.setdefault(feature_hash, set()).add(row.identity.is_attack)
        key = (row.source_row.values, row.identity.is_attack)
        equivalence_classes.setdefault(key, []).append(row)

    canonical_rows = tuple(
        group[0] for _, group in sorted(equivalence_classes.items(), key=lambda item: _provenance_key(item[1][0]))
    )
    deduplication = CICIoT2023DeduplicationResult(
        canonical_rows=canonical_rows,
        duplicate_rows_removed=len(ordered_rows) - len(canonical_rows),
        conflicting_label_feature_group_count=sum(len(labels) > 1 for labels in labels_by_feature_hash.values()),
    )

    benign_classes = [
        group
        for _, group in sorted(equivalence_classes.items(), key=lambda item: _equivalence_hash(item[0]))
        if not group[0].identity.is_attack
    ]
    generator = Random(materialization.split_seed.value)
    generator.shuffle(benign_classes)
    train: list[CICIoT2023MaterializedRow] = []
    calibration: list[CICIoT2023MaterializedRow] = []
    test: list[CICIoT2023MaterializedRow] = [
        group[0]
        for _, group in sorted(equivalence_classes.items(), key=lambda item: _equivalence_hash(item[0]))
        if group[0].identity.is_attack
    ]
    for group in benign_classes:
        draw = generator.random()
        canonical = group[0]
        if draw < train_ratio:
            train.append(canonical)
        elif draw < train_ratio + calibration_ratio:
            calibration.append(canonical)
        else:
            test.append(canonical)
    return CICIoT2023SplitRows(
        train=tuple(sorted(train, key=_provenance_key)),
        calibration=tuple(sorted(calibration, key=_provenance_key)),
        test=tuple(sorted(test, key=_provenance_key)),
        deduplication=deduplication,
    )


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
    """Deduplicate merged CSV rows in SQLite, then stream the configured split to Parquet."""
    if not source_paths or batch_size <= 0:
        raise ValueError("CICIoT2023 materialization requires source files and a positive Parquet batch size")
    if materialization.split_method != "random_fractional" or materialization.split_seed is None:
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
                            bytes.fromhex(_equivalence_hash((row.source_row.values, row.identity.is_attack))),
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


def _provenance_key(row: CICIoT2023MaterializedRow) -> tuple[str, int]:
    return (row.identity.source_path.as_posix(), row.identity.source_row_index)


def _feature_hash(values: tuple[float, ...]) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(_serialize_features(values))
    return digest.hexdigest()


def _equivalence_hash(equivalence_key: tuple[tuple[float, ...], bool]) -> str:
    feature_values, is_attack = equivalence_key
    digest = hashlib.blake2b(digest_size=32)
    digest.update(bytes((is_attack,)))
    digest.update(_serialize_features(feature_values))
    return digest.hexdigest()


def _serialize_features(values: tuple[float, ...]) -> bytes:
    return struct.pack(f"!{len(values)}d", *values)


def _deserialize_features(payload: bytes, feature_count: int) -> tuple[float, ...]:
    if len(payload) != feature_count * 8:
        raise ValueError("CICIoT2023 equivalence index has an invalid feature payload width")
    return struct.unpack(f"!{feature_count}d", payload)


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023MaterializationPayload:
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes | None = None


class CICIoT2023Adapter:
    """CICIoT2023 dataset materializer: merged-source pseudo-client, dedup, random split, Parquet output."""

    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.CICIOT2023

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
    ) -> CICIoT2023MaterializationPayload:
        if partition_condition is not None or partition_seed_contract is not None:
            raise ValueError("CICIoT2023 does not support partition-condition materialization")
        inspection = dataset.inspection_contract
        if inspection.benign_label is None:
            raise ValueError("CICIoT2023 configured benign label is absent")

        primary_tree = inspection.source_trees[0]
        feature_headers = primary_tree.required_headers[:-1]
        label_header = primary_tree.required_headers[-1]
        merged_root = dataset.paths.raw_data_root / primary_tree.root.value
        chunk_row_count = 100_000

        source_paths = tuple(entry.source_path for entry in inventory.entries)
        unprocessed_payload = staging_root / "unprocessed.parquet"

        report = write_ciciot2023_materialized_parquet(
            source_paths,
            unprocessed_payload,
            feature_headers,
            label_header,
            merged_root.resolve(),
            inspection.benign_label,
            materialization,
            chunk_row_count,
        )

        feature_columns = dataset.field_schema.model_features
        if feature_columns is None:
            raise ValueError("CICIoT2023 materialization requires configured model features")
        payload_file = staging_root / "materialized.parquet"
        normalization = normalize_materialized_parquet(
            unprocessed_payload,
            payload_file,
            feature_columns=feature_columns.order,
            strategy=materialization.normalization_strategy,
            scope=materialization.normalization_scope,
        )
        return CICIoT2023MaterializationPayload(
            staged_path=payload_file,
            row_count=report.written_rows,
            preprocessing_evidence=normalization.encode(),
        )
