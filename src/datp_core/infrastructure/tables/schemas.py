"""Pandera DataFrame schema contracts validating physical tabular artifacts."""

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


class ThresholdFrameSchema(pa.DataFrameModel):
    client_id: str
    threshold: float = pa.Field(ge=0.0)  # type: ignore
    owner_kind: str


class ClientMetricFrameSchema(pa.DataFrameModel):
    client_id: str
    false_positives: int = pa.Field(ge=0)  # type: ignore
    true_negatives: int = pa.Field(ge=0)  # type: ignore
    false_positive_rate: float = pa.Field(ge=0.0, le=1.0)  # type: ignore


def validate_calibration_score_frame(df: pl.DataFrame) -> pl.DataFrame:
    return CalibrationScoreFrameSchema.validate(df)


def validate_test_score_frame(df: pl.DataFrame) -> pl.DataFrame:
    return TestScoreFrameSchema.validate(df)


def validate_threshold_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ThresholdFrameSchema.validate(df)


def validate_client_metric_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ClientMetricFrameSchema.validate(df)
