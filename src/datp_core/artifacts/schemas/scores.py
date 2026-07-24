"""Physical Pandera schemas for calibration and test score frames."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl


class CalibrationScoreFrameSchema(pa.DataFrameModel):
    client_id: str
    score: float = pa.Field(ge=0.0)  # type: ignore


class TestScoreFrameSchema(pa.DataFrameModel):
    client_id: str
    score: float = pa.Field(ge=0.0)  # type: ignore
    label: int = pa.Field(isin=[0, 1])  # type: ignore


def validate_calibration_score_frame(df: pl.DataFrame) -> pl.DataFrame:
    return CalibrationScoreFrameSchema.validate(df)


def validate_test_score_frame(df: pl.DataFrame) -> pl.DataFrame:
    return TestScoreFrameSchema.validate(df)
