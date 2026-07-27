"""Physical Pandera schema for the client metric frame."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl

from datp_core.evaluation.enums import MetricStatus

_FPR_STATUSES = (
    MetricStatus.AVAILABLE.value,
    MetricStatus.UNDEFINED_ZERO_DENOMINATOR.value,
    MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value,
    MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value,
)

_TPR_STATUSES = (
    MetricStatus.AVAILABLE.value,
    MetricStatus.UNDEFINED_ZERO_DENOMINATOR.value,
    MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value,
    MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value,
    MetricStatus.UNAVAILABLE_INVALID_ATTACK_ASSIGNMENT.value,
    MetricStatus.UNAVAILABLE_UNSUPPORTED_REGIME.value,
)

_CLASS_DEPENDENT_STATUSES = (
    MetricStatus.AVAILABLE.value,
    MetricStatus.UNDEFINED_ZERO_DENOMINATOR.value,
    MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value,
    MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value,
    MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value,
)

_AUROC_STATUSES = (
    MetricStatus.AVAILABLE.value,
    MetricStatus.UNAVAILABLE_SINGLE_CLASS.value,
)


class ClientMetricFrameSchema(pa.DataFrameModel):
    client_id: str = pa.Field(unique=True)  # type: ignore[operator]
    true_positives: int | None = pa.Field(nullable=True, ge=0)  # type: ignore[operator]
    false_positives: int | None = pa.Field(nullable=True, ge=0)  # type: ignore[operator]
    true_negatives: int | None = pa.Field(nullable=True, ge=0)  # type: ignore[operator]
    false_negatives: int | None = pa.Field(nullable=True, ge=0)  # type: ignore[operator]
    false_positive_rate: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore[operator]
    false_positive_rate_status: str = pa.Field(isin=list(_FPR_STATUSES))  # type: ignore[operator]
    true_positive_rate: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore[operator]
    true_positive_rate_status: str = pa.Field(isin=list(_TPR_STATUSES))  # type: ignore[operator]
    balanced_accuracy: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore[operator]
    balanced_accuracy_status: str = pa.Field(isin=list(_CLASS_DEPENDENT_STATUSES))  # type: ignore[operator]
    macro_f1: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore[operator]
    macro_f1_status: str = pa.Field(isin=list(_CLASS_DEPENDENT_STATUSES))  # type: ignore[operator]
    auroc: float | None = pa.Field(nullable=True, ge=0.0, le=1.0)  # type: ignore[operator]
    auroc_status: str = pa.Field(isin=list(_AUROC_STATUSES))  # type: ignore[operator]
    policy_id: str = pa.Field(nullable=False)  # type: ignore[operator]
    seed: int = pa.Field(nullable=False, ge=0)  # type: ignore[operator]


def validate_client_metric_frame(df: pl.DataFrame) -> pl.DataFrame:
    return ClientMetricFrameSchema.validate(df)
