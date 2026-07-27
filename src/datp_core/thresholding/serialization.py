"""Threshold frame serialization and diagnostics JSON encoding."""

from __future__ import annotations

import polars as pl

from datp_core.artifacts.schemas.columns import ThresholdColumn
from datp_core.artifacts.schemas.thresholds import THRESHOLD_FRAME_DTYPES
from datp_core.core.identifiers import ClientId, PopulationId
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    ThresholdDiagnostics,
    ThresholdSet,
)


def calibration_to_benign_scores(
    scores: pl.DataFrame, population_id: PopulationId | None
) -> tuple[BenignCalibrationScores, ...]:
    """Convert a polars calibration DataFrame into typed BenignCalibrationScores."""
    return tuple(
        BenignCalibrationScores(
            client_id=ClientId(str(client_id[0])),
            values=tuple(float(value) for value in rows["score"].to_list()),
            population_id=population_id,
        )
        for client_id, rows in scores.group_by("client_id", maintain_order=True)
    )


def threshold_set_to_frame(threshold_set: ThresholdSet) -> pl.DataFrame:
    """Serialize a ThresholdSet to a polars DataFrame."""
    return pl.DataFrame(
        {
            ThresholdColumn.CLIENT_ID.value: [rec.client_id.value for rec in threshold_set.values],
            ThresholdColumn.THRESHOLD.value: [float(rec.threshold) for rec in threshold_set.values],
            ThresholdColumn.POLICY_KIND.value: [rec.policy_kind.value for rec in threshold_set.values],
            ThresholdColumn.SCOPE.value: [rec.scope.value for rec in threshold_set.values],
            ThresholdColumn.EFFECTIVE_LAMBDA.value: [rec.effective_lambda for rec in threshold_set.values],
            ThresholdColumn.CLUSTER_LABEL.value: [rec.cluster_label for rec in threshold_set.values],
            ThresholdColumn.FINITE_SAMPLE_RANK.value: [rec.finite_sample_rank for rec in threshold_set.values],
            ThresholdColumn.POLICY_ID.value: [threshold_set.policy_id.value] * len(threshold_set.values),
            ThresholdColumn.TARGET_QUANTILE.value: [threshold_set.target_quantile.value] * len(threshold_set.values),
        },
        schema=pl.Schema(THRESHOLD_FRAME_DTYPES),
    )


def diagnostics_to_json(diagnostics: ThresholdDiagnostics | None) -> bytes:
    """Serialize diagnostics losslessly to JSON bytes."""
    if diagnostics is None:
        return b"{}"
    return diagnostics.model_dump_json(
        by_alias=False,
        exclude_none=True,
    ).encode("utf-8")
