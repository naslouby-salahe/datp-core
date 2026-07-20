"""N-BaIoT path-derived identity and label materialization rules."""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from attrs import define

from datp_core.domain.datasets import DatasetMaterialization
from datp_core.infrastructure.datasets.csv_source import SourceRow, SourceRowFailure, iter_numeric_csv_source


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTMaterializedRow:
    """One N-BaIoT numeric row with configured identity and binary label semantics."""

    client_id: str
    attack_family: str | None
    is_attack: bool
    source_row: SourceRow


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTSplitRows:
    """Configured N-BaIoT chronological split, including intentionally excluded gaps."""

    train: tuple[NBaIoTMaterializedRow, ...]
    calibration: tuple[NBaIoTMaterializedRow, ...]
    test_benign: tuple[NBaIoTMaterializedRow, ...]
    test_attack: tuple[NBaIoTMaterializedRow, ...]
    excluded_gap_rows: tuple[NBaIoTMaterializedRow, ...]


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTChronologicalBoundaries:
    """Zero-based boundaries for one source file's configured chronological split."""

    train_end: int
    first_gap_end: int
    calibration_end: int
    second_gap_end: int
    row_count: int

    def role_for_benign_index(self, index: int) -> str:
        if not 0 <= index < self.row_count:
            raise IndexError("N-BaIoT benign source-row index is outside the configured source count")
        if index < self.train_end:
            return "train"
        if index < self.first_gap_end:
            return "excluded_gap"
        if index < self.calibration_end:
            return "calibration"
        if index < self.second_gap_end:
            return "excluded_gap"
        return "test"


def materialize_nbaiot_source_row(
    source_row: SourceRow,
    dataset_root: Path,
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
) -> NBaIoTMaterializedRow:
    """Derive client and attack identity from the configured N-BaIoT source path."""
    try:
        relative_path = source_row.source_path.relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError("N-BaIoT source row is outside the configured dataset root") from exc
    if len(relative_path.parts) < 2:
        raise ValueError("N-BaIoT source row has no configured device-directory identity")
    client_id = relative_path.parts[0]
    if relative_path.name == benign_filename:
        return NBaIoTMaterializedRow(
            client_id=client_id,
            attack_family=None,
            is_attack=False,
            source_row=source_row,
        )
    if len(relative_path.parts) >= 3 and relative_path.parts[1] in attack_family_directories:
        return NBaIoTMaterializedRow(
            client_id=client_id,
            attack_family=relative_path.parts[1],
            is_attack=True,
            source_row=source_row,
        )
    raise ValueError("N-BaIoT source row does not satisfy configured benign or attack path semantics")


def split_nbaiot_chronological_gapped_rows(
    rows: tuple[NBaIoTMaterializedRow, ...],
    train_fraction: float,
    first_gap_fraction: float,
    calibration_fraction: float,
    second_gap_fraction: float,
    test_fraction: float,
) -> NBaIoTSplitRows:
    """Apply configured per-client chronological fractions without shuffling or leakage."""
    fractions = (train_fraction, first_gap_fraction, calibration_fraction, second_gap_fraction, test_fraction)
    if any(not 0.0 <= fraction <= 1.0 for fraction in fractions) or not math.isclose(
        sum(fractions), 1.0, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError("N-BaIoT chronological split fractions must be probabilities summing exactly to one")
    benign = tuple(row for row in rows if not row.is_attack)
    attack = tuple(row for row in rows if row.is_attack)
    if tuple(sorted(benign, key=lambda row: row.source_row.source_row_index)) != benign:
        raise ValueError("N-BaIoT benign rows must be supplied in ascending source-row order")
    row_count = len(benign)
    train_end = int(train_fraction * row_count)
    first_gap_end = train_end + int(first_gap_fraction * row_count)
    calibration_end = first_gap_end + int(calibration_fraction * row_count)
    second_gap_end = calibration_end + int(second_gap_fraction * row_count)
    return NBaIoTSplitRows(
        train=benign[:train_end],
        calibration=benign[first_gap_end:calibration_end],
        test_benign=benign[second_gap_end:],
        test_attack=attack,
        excluded_gap_rows=benign[train_end:first_gap_end] + benign[calibration_end:second_gap_end],
    )


def calculate_nbaiot_chronological_boundaries(
    row_count: int, materialization: DatasetMaterialization
) -> NBaIoTChronologicalBoundaries:
    """Calculate the authored N-BaIoT source-file boundaries before streaming a second pass."""
    if row_count < 0:
        raise ValueError("N-BaIoT source row count cannot be negative")
    if materialization.split_method != "chronological_gapped":
        raise ValueError("N-BaIoT chronological materialization requires the configured chronological_gapped method")
    train_end = int(float(materialization.ratio("train")) * row_count)
    first_gap_end = train_end + int(float(materialization.ratio("gap_1")) * row_count)
    calibration_end = first_gap_end + int(float(materialization.ratio("calibration")) * row_count)
    second_gap_end = calibration_end + int(float(materialization.ratio("gap_2")) * row_count)
    return NBaIoTChronologicalBoundaries(
        train_end=train_end,
        first_gap_end=first_gap_end,
        calibration_end=calibration_end,
        second_gap_end=second_gap_end,
        row_count=row_count,
    )


def write_nbaiot_source_parquet(
    source_path: Path,
    target_path: Path,
    dataset_root: Path,
    feature_headers: tuple[str, ...],
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
    materialization: DatasetMaterialization,
    batch_size: int,
) -> int:
    """Validate/count a source then stream its configured split to a Parquet file."""
    if batch_size <= 0:
        raise ValueError("N-BaIoT Parquet batch size must be positive")
    valid_benign_count = 0
    for result in iter_numeric_csv_source(source_path, feature_headers):
        if isinstance(result, SourceRowFailure):
            raise ValueError(f"N-BaIoT source validation rejected row {result.source_row_index} in {source_path}")
        if not materialize_nbaiot_source_row(
            result, dataset_root, benign_filename, attack_family_directories
        ).is_attack:
            valid_benign_count += 1
    boundaries = calculate_nbaiot_chronological_boundaries(valid_benign_count, materialization)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            ("split", pa.string()),
            ("client_id", pa.string()),
            ("is_attack", pa.bool_()),
            ("attack_family", pa.string()),
            ("source_path", pa.string()),
            ("source_row_index", pa.int64()),
            *((header, pa.float64()) for header in feature_headers),
        ]
    )
    benign_index = 0
    written = 0
    records: dict[str, list[object]] = {field.name: [] for field in schema}
    with pq.ParquetWriter(target_path, schema, compression="zstd", use_dictionary=False) as writer:
        for result in iter_numeric_csv_source(source_path, feature_headers):
            if isinstance(result, SourceRowFailure):
                raise ValueError(f"N-BaIoT source changed between validation and write: {source_path}")
            row = materialize_nbaiot_source_row(result, dataset_root, benign_filename, attack_family_directories)
            role = "test" if row.is_attack else boundaries.role_for_benign_index(benign_index)
            benign_index += not row.is_attack
            if role == "excluded_gap":
                continue
            records["split"].append(role)
            records["client_id"].append(row.client_id)
            records["is_attack"].append(row.is_attack)
            records["attack_family"].append(row.attack_family)
            records["source_path"].append(row.source_row.source_path.as_posix())
            records["source_row_index"].append(row.source_row.source_row_index)
            for header, value in zip(feature_headers, row.source_row.values, strict=True):
                records[header].append(value)
            if len(records["split"]) == batch_size:
                writer.write_table(pa.table(records, schema=schema))
                written += len(records["split"])
                records = {field.name: [] for field in schema}
        if records["split"]:
            writer.write_table(pa.table(records, schema=schema))
            written += len(records["split"])
    return written


def consolidate_nbaiot_parquet_sources(source_paths: tuple[Path, ...], target_path: Path, batch_size: int) -> int:
    """Consolidate staged source Parquet files through bounded Arrow record batches."""
    if not source_paths:
        raise ValueError("N-BaIoT consolidation requires at least one staged source file")
    if batch_size <= 0:
        raise ValueError("N-BaIoT consolidation batch size must be positive")
    first_file = pq.ParquetFile(source_paths[0])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with pq.ParquetWriter(target_path, first_file.schema_arrow, compression="zstd", use_dictionary=False) as writer:
        for source_path in source_paths:
            parquet_file = pq.ParquetFile(source_path)
            if parquet_file.schema_arrow != first_file.schema_arrow:
                raise ValueError("N-BaIoT staged Parquet schema mismatch")
            for batch in parquet_file.iter_batches(batch_size=batch_size):
                writer.write_batch(batch)
                written += batch.num_rows
    return written


def split_nbaiot_using_resolved_materialization(
    rows: tuple[NBaIoTMaterializedRow, ...], materialization: DatasetMaterialization
) -> NBaIoTSplitRows:
    """Apply the exact resolved authored N-BaIoT chronological split contract."""
    if materialization.split_method != "chronological_gapped":
        raise ValueError("N-BaIoT chronological materialization requires the configured chronological_gapped method")
    return split_nbaiot_chronological_gapped_rows(
        rows,
        float(materialization.ratio("train")),
        float(materialization.ratio("gap_1")),
        float(materialization.ratio("calibration")),
        float(materialization.ratio("gap_2")),
        float(materialization.ratio("test")),
    )


def encode_nbaiot_split_as_parquet(split: NBaIoTSplitRows, feature_headers: tuple[str, ...]) -> bytes:
    """Encode a complete typed N-BaIoT split as deterministic Parquet payload bytes."""
    ordered_rows = (
        *(("train", row) for row in split.train),
        *(("calibration", row) for row in split.calibration),
        *(("test", row) for row in split.test_benign),
        *(("test", row) for row in split.test_attack),
    )
    records: dict[str, list[object]] = {
        "split": [],
        "client_id": [],
        "is_attack": [],
        "attack_family": [],
        "source_path": [],
        "source_row_index": [],
    }
    records.update({header: [] for header in feature_headers})
    for split_name, materialized_row in ordered_rows:
        values = materialized_row.source_row.values
        if len(values) != len(feature_headers):
            raise ValueError("N-BaIoT source row width does not match the resolved feature schema")
        records["split"].append(split_name)
        records["client_id"].append(materialized_row.client_id)
        records["is_attack"].append(materialized_row.is_attack)
        records["attack_family"].append(materialized_row.attack_family)
        records["source_path"].append(materialized_row.source_row.source_path.as_posix())
        records["source_row_index"].append(materialized_row.source_row.source_row_index)
        for header, value in zip(feature_headers, values, strict=True):
            records[header].append(value)
    table = pa.table(records)
    payload = BytesIO()
    pq.write_table(table, payload, compression="zstd", use_dictionary=False)
    return payload.getvalue()
