"""Physical Pandera schema for the client metric frame."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl


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
        isin=[
            "available",
            "unavailable_missing_attack_class",
            "unavailable_invalid_attack_assignment",
            "unavailable_ineligible_client",
        ]
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
    auroc: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore
    auroc_status: str = pa.Field(isin=["available", "unavailable_single_class", "unavailable_ineligible_client"])  # type: ignore


def validate_client_metric_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ClientMetricFrameSchema.validate(df)
