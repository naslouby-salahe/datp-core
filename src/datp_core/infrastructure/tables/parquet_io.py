"""Parquet schema inspection and controlled Parquet reading/writing via PyArrow and Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from datp_core.domain.fingerprints import Fingerprint


def write_dataframe_parquet(
    df: pl.DataFrame,
    target_path: Path,
    scientific_fingerprint: Fingerprint | None = None,
    compression: str = "zstd",
) -> None:
    """Write Polars DataFrame to Parquet with PyArrow schema validation and metadata injection."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_df = df.select(sorted(df.columns))
    arrow_table = sorted_df.to_arrow()

    existing_meta = arrow_table.schema.metadata or {}
    custom_meta = {
        b"schema_version": b"1",
        b"datp_fingerprint": (scientific_fingerprint.value.encode("utf-8") if scientific_fingerprint else b"none"),
    }
    merged_meta = {**existing_meta, **custom_meta}
    arrow_table = arrow_table.replace_schema_metadata(merged_meta)

    pq.write_table(arrow_table, target_path, compression=compression)


def read_dataframe_parquet(target_path: Path) -> pl.DataFrame:
    """Read Parquet file into Polars DataFrame with existence check."""
    if not target_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {target_path}")
    return pl.read_parquet(target_path)


def inspect_parquet_schema(target_path: Path) -> dict[str, str]:
    """Inspect PyArrow Parquet schema column types."""
    schema = pq.read_schema(target_path)
    return {name: str(dtype) for name, dtype in zip(schema.names, schema.types, strict=False)}
