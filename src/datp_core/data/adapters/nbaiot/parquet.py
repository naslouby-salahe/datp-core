"""N-BaIoT Parquet schema, writing, and consolidation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from datp_core.data.adapters.nbaiot.models import NBaIoTMaterializedRow, NBaIoTSplitRows
from datp_core.data.adapters.nbaiot.splitting import (
    calculate_nbaiot_chronological_boundaries,
    random_fractional_roles,
)
from datp_core.data.contracts.enums import SplitMethod
from datp_core.data.contracts.materialization import DatasetMaterialization
from datp_core.data.sources.models import SourceRow


def materialize_nbaiot_source_row(
    source_row: SourceRow,
    dataset_root: Path,
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
) -> NBaIoTMaterializedRow:
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


def _resolve_nbaiot_source_classification(
    source_path: Path,
    dataset_root: Path,
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
) -> tuple[str, bool, str | None]:
    """Return (client_id, is_attack, attack_family) from the source path once."""
    try:
        relative_path = source_path.relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError("N-BaIoT source path is outside the configured dataset root") from exc
    if len(relative_path.parts) < 2:
        raise ValueError("N-BaIoT source path has no configured device-directory identity")
    client_id = relative_path.parts[0]
    is_attack = relative_path.name != benign_filename
    if not is_attack:
        return (client_id, False, None)
    if len(relative_path.parts) >= 3 and relative_path.parts[1] in attack_family_directories:
        return (client_id, True, relative_path.parts[1])
    raise ValueError("N-BaIoT source path does not satisfy configured benign or attack path semantics")


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

    client_id, is_attack_source, attack_family = _resolve_nbaiot_source_classification(
        source_path, dataset_root, benign_filename, attack_family_directories
    )

    df = pl.read_csv(source_path)
    for header in feature_headers:
        if header not in df.columns:
            raise ValueError(f"N-BaIoT source {source_path} is missing required header '{header}'")

    df = df.select(*feature_headers)
    for header in feature_headers:
        df = df.with_columns(pl.col(header).cast(pl.Float64))
        bad = df.filter(pl.col(header).is_null() | ~pl.col(header).is_finite())
        if bad.height > 0:
            raise ValueError(f"N-BaIoT source {source_path}: invalid numeric value in column '{header}'")

    df = df.with_row_index("__source_order")
    total_rows = df.height

    if is_attack_source:
        df = df.with_columns(
            pl.lit("test").alias("split"),
            pl.lit(client_id).alias("client_id"),
            pl.lit(True).alias("is_attack"),
            pl.lit(attack_family).alias("attack_family"),
            pl.lit(source_path.as_posix()).alias("source_path"),
            (pl.col("__source_order") + 1).alias("source_row_index"),
        )
    else:
        benign_count = total_rows
        random_roles = (
            random_fractional_roles(benign_count, materialization, source_path)
            if materialization.split_method == SplitMethod.RANDOM_FRACTIONAL
            else None
        )

        if random_roles is not None:
            df = df.with_columns(pl.Series("__role", random_roles))
            df = df.with_columns(pl.col("__role").alias("split")).drop("__role")
        else:
            boundaries = calculate_nbaiot_chronological_boundaries(benign_count, materialization)
            df = df.with_columns(
                pl.when(pl.col("__source_order") < boundaries.train_end)
                .then(pl.lit("train"))
                .when(pl.col("__source_order") < boundaries.first_gap_end)
                .then(pl.lit("excluded_gap"))
                .when(pl.col("__source_order") < boundaries.calibration_end)
                .then(pl.lit("calibration"))
                .when(pl.col("__source_order") < boundaries.second_gap_end)
                .then(pl.lit("excluded_gap"))
                .otherwise(pl.lit("test"))
                .alias("split")
            )

        df = df.with_columns(
            pl.lit(client_id).alias("client_id"),
            pl.lit(False).alias("is_attack"),
            pl.lit(None, dtype=pl.String).alias("attack_family"),
            pl.lit(source_path.as_posix()).alias("source_path"),
            (pl.col("__source_order") + 1).alias("source_row_index"),
        )

    df = df.filter(pl.col("split") != "excluded_gap").drop("__source_order")
    output_columns = [
        "split",
        "client_id",
        "is_attack",
        "attack_family",
        "source_path",
        "source_row_index",
        *feature_headers,
    ]
    df = df.select(*output_columns)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(target_path, compression="zstd")
    return df.height


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
    records: list[dict[str, object]] = []
    for split_name, materialized_row in ordered_rows:
        values = materialized_row.source_row.values
        if len(values) != len(feature_headers):
            raise ValueError("N-BaIoT source row width does not match the resolved feature schema")
        record: dict[str, object] = {
            "split": split_name,
            "client_id": materialized_row.client_id,
            "is_attack": materialized_row.is_attack,
            "attack_family": materialized_row.attack_family,
            "source_path": materialized_row.source_row.source_path.as_posix(),
            "source_row_index": materialized_row.source_row.source_row_index,
        }
        record.update(zip(feature_headers, values, strict=True))
        records.append(record)
    payload = BytesIO()
    pl.DataFrame(records).write_parquet(payload, compression="zstd")
    return payload.getvalue()
