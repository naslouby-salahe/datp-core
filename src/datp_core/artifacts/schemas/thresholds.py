"""Physical Pandera schema for the threshold frame."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl

from datp_core.artifacts.schemas.columns import ThresholdColumn

# Canonical column-to-dtype mapping for threshold frames.
# Used at the serialisation boundary to construct typed DataFrames.
THRESHOLD_FRAME_DTYPES: dict[str, pl.DataType] = {
    ThresholdColumn.CLIENT_ID.value: pl.String,
    ThresholdColumn.THRESHOLD.value: pl.Float64,
    ThresholdColumn.POLICY_KIND.value: pl.String,
    ThresholdColumn.SCOPE.value: pl.String,
    ThresholdColumn.EFFECTIVE_LAMBDA.value: pl.Float64,
    ThresholdColumn.CLUSTER_LABEL.value: pl.Int64,
    ThresholdColumn.FINITE_SAMPLE_RANK.value: pl.Int64,
    ThresholdColumn.POLICY_ID.value: pl.String,
    ThresholdColumn.TARGET_QUANTILE.value: pl.Float64,
}


class ThresholdFrameSchema(pa.DataFrameModel):
    client_id: str
    threshold: float = pa.Field(ge=0.0)  # type: ignore[operator]
    policy_kind: str
    scope: str
    effective_lambda: float | None = pa.Field(nullable=True, ge=0.0)  # type: ignore[operator]
    cluster_label: int | None = pa.Field(nullable=True, ge=0)  # type: ignore[operator]
    finite_sample_rank: int | None = pa.Field(nullable=True, ge=1)  # type: ignore[operator]
    policy_id: str
    target_quantile: float = pa.Field(ge=0.0, le=1.0)  # type: ignore[operator]


def validate_threshold_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ThresholdFrameSchema.validate(df)
