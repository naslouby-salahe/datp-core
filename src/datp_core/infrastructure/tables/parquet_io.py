"""Parquet schema inspection and controlled Parquet reading/writing via PyArrow and Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pyarrow.parquet as pq


def write_dataframe_parquet(df: pl.DataFrame, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(target_path)


def read_dataframe_parquet(target_path: Path) -> pl.DataFrame:
    if not target_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {target_path}")
    return pl.read_parquet(target_path)


def inspect_parquet_schema(target_path: Path) -> dict[str, str]:
    schema = pq.read_schema(target_path)
    return {name: str(dtype) for name, dtype in zip(schema.names, schema.types, strict=False)}
