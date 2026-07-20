"""Xarray-backed labeled multidimensional result views."""

from __future__ import annotations

import polars as pl
import xarray as xr


def build_multidimensional_metric_cube(
    df: pl.DataFrame,
    dim_cols: tuple[str, ...] = ("experiment", "seed", "threshold_policy", "client_id"),
    value_col: str = "false_positive_rate",
) -> xr.DataArray:
    """Convert a long-form Polars metric DataFrame into a labeled Xarray DataArray multi-cube."""
    if df.is_empty():
        raise ValueError("Cannot build Xarray metric cube from empty DataFrame")
    for col in dim_cols:
        if col not in df.columns:
            raise ValueError(f"Dimension column '{col}' missing from DataFrame")
    if value_col not in df.columns:
        raise ValueError(f"Value column '{value_col}' missing from DataFrame")

    pandas_df = df.select(list(dim_cols) + [value_col]).to_pandas()

    # Verify unique coordinate index
    if pandas_df.duplicated(subset=list(dim_cols)).any():
        pandas_df = pandas_df.drop_duplicates(subset=list(dim_cols), keep="first")

    indexed = pandas_df.set_index(list(dim_cols))
    xr_dataset = indexed.to_xarray()
    return xr_dataset[value_col]
