"""Physical Pandera schema for the threshold frame."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl


class ThresholdFrameSchema(pa.DataFrameModel):
    client_id: str
    threshold: float = pa.Field(ge=0.0)  # type: ignore
    owner_kind: str
    finite_sample_rank: int | None = pa.Field(nullable=True, ge=1)  # type: ignore
    attainability_status: str | None = pa.Field(nullable=True, isin=["attainable", "unattainable"])  # type: ignore


def validate_threshold_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ThresholdFrameSchema.validate(df)
