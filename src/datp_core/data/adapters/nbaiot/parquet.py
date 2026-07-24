"""N-BaIoT Parquet schema, writing, and consolidation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.data.adapters.nbaiot.models import NBaIoTMaterializedRow, NBaIoTSplitRows
from datp_core.data.adapters.nbaiot.splitting import (
    calculate_nbaiot_chronological_boundaries,
    random_fractional_roles,
)
from datp_core.data.contracts.enums import SplitMethod
from datp_core.data.contracts.materialization import DatasetMaterialization
from datp_core.data.sources.csv import iter_numeric_csv_source
from datp_core.data.sources.models import SourceRowFailure


def materialize_nbaiot_source_row(
    source_row: "SourceRow",
    dataset_root: Path,
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
) -> NBaIoTMaterializedRow:
    from datp_core.data.sources.models import SourceRow

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
    random_roles = (
        random_fractional_roles(valid_benign_count, materialization, source_path)
        if materialization.split_method == SplitMethod.RANDOM_FRACTIONAL
        else None
    )
    boundaries = (
        calculate_nbaiot_chronological_boundaries(valid_benign_count, materialization) if random_roles is None else None
    )
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
            if row.is_attack:
                role = "test"
            elif random_roles is not None:
                role = random_roles[benign_index]
            else:
                if boundaries is None:
                    raise ValueError("N-BaIoT materialization requires either random roles or chronological boundaries")
                role = boundaries.role_for_benign_index(benign_index)
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


def encode_nbaiot_split_as_parquet(split: NBaIoTSplitRows, feature_headers: tuple[str, ...]) -> bytes:
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
