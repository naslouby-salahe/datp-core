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
    finite_sample_rank: int | None = pa.Field(nullable=True, ge=1)  # type: ignore
    attainability_status: str | None = pa.Field(nullable=True, isin=["attainable", "unattainable"])  # type: ignore


class ClientMetricFrameSchema(pa.DataFrameModel):
    client_id: str
    true_positives: int = pa.Field(ge=0)  # type: ignore
    false_positives: int = pa.Field(ge=0)  # type: ignore
    true_negatives: int = pa.Field(ge=0)  # type: ignore
    false_negatives: int = pa.Field(ge=0)  # type: ignore
    false_positive_rate: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore
    false_positive_rate_status: str = pa.Field(  # type: ignore
        isin=["available", "unavailable_missing_benign_class", "unavailable_ineligible_client"]
    )
    true_positive_rate: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore
    true_positive_rate_status: str = pa.Field(  # type: ignore
        isin=["available", "unavailable_missing_attack_class", "unavailable_ineligible_client"]
    )
    balanced_accuracy: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore
    balanced_accuracy_status: str = pa.Field(
        isin=[
            "available",
            "unavailable_missing_benign_class",
            "unavailable_missing_attack_class",
            "unavailable_ineligible_client",
        ]
    )  # type: ignore
    macro_f1: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore
    macro_f1_status: str = pa.Field(
        isin=[
            "available",
            "unavailable_missing_benign_class",
            "unavailable_missing_attack_class",
            "undefined_zero_denominator",
            "unavailable_ineligible_client",
        ]
    )  # type: ignore


def validate_calibration_score_frame(df: pl.DataFrame) -> pl.DataFrame:
    return CalibrationScoreFrameSchema.validate(df)


def validate_test_score_frame(df: pl.DataFrame) -> pl.DataFrame:
    return TestScoreFrameSchema.validate(df)


def validate_threshold_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ThresholdFrameSchema.validate(df)


def validate_client_metric_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ClientMetricFrameSchema.validate(df)
