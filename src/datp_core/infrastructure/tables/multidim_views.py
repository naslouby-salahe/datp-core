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
    pandas_df = df.select(list(dim_cols) + [value_col]).to_pandas()
    indexed = pandas_df.set_index(list(dim_cols))
    xr_dataset = indexed.to_xarray()
    return xr_dataset[value_col]
