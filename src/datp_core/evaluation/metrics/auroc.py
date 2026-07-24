"""Per-client AUROC computation using raw scores and labels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.metrics import roc_auc_score

from datp_core.evaluation.metrics.models import MetricStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientAuroc:
    value: float | None
    status: MetricStatus

    @classmethod
    def available(cls, value: float) -> ClientAuroc:
        return cls(value=value, status=MetricStatus.AVAILABLE)

    @classmethod
    def unavailable_single_class(cls) -> ClientAuroc:
        return cls(value=None, status=MetricStatus.UNAVAILABLE_SINGLE_CLASS)


def compute_roc_auc(labels: np.ndarray, scores: np.ndarray) -> ClientAuroc:
    if len(np.unique(labels)) < 2:
        return ClientAuroc.unavailable_single_class()
    return ClientAuroc.available(float(roc_auc_score(labels, scores)))


def compute_client_auroc(df: pl.DataFrame) -> pl.DataFrame:
    if df.is_empty():
        raise ValueError("Cannot compute AUROC on empty DataFrame")
    if "score" not in df.columns or "label" not in df.columns:
        raise ValueError("AUROC computation requires score and label columns")

    auroc_records: list[dict[str, object]] = []
    for (client_id,), group in df.group_by("client_id", maintain_order=True):
        labels = group["label"].to_numpy()
        scores = group["score"].to_numpy()
        result: ClientAuroc = compute_roc_auc(labels, scores)
        auroc_records.append(
            {
                "client_id": client_id,
                "auroc": result.value,
                "auroc_status": result.status.value,
            }
        )

    return pl.DataFrame(auroc_records, schema={"client_id": pl.String, "auroc": pl.Float64, "auroc_status": pl.String})
