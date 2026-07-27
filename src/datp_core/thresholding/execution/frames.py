"""Threshold frame conversion: calibration scores to ThresholdSet, ThresholdSet to output frame."""

from __future__ import annotations

import json

import polars as pl

from datp_core.core.identifiers import ClientId, PopulationId
from datp_core.thresholding.estimation.models import (
    MatchedExceedanceDiagnostics,
    ThresholdSet,
)
from datp_core.thresholding.policies.common import BenignCalibrationScores


def calibration_to_benign_scores(
    scores: pl.DataFrame, population_id: PopulationId | None
) -> tuple[BenignCalibrationScores, ...]:
    return tuple(
        BenignCalibrationScores(
            client_id=ClientId(str(client_id[0])),
            values=tuple(float(value) for value in rows["score"].to_list()),
            population_id=population_id,
        )
        for client_id, rows in scores.group_by("client_id", maintain_order=True)
    )


def threshold_set_to_frame(threshold_set: ThresholdSet) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "client_id": [record.client_id.value for record in threshold_set.values],
            "threshold": [float(record.threshold) for record in threshold_set.values],
            "owner_kind": [record.owner.value for record in threshold_set.values],
            "effective_lambda": [record.effective_lambda for record in threshold_set.values],
            "cluster_label": [record.cluster_label for record in threshold_set.values],
            "finite_sample_rank": [record.finite_sample_rank for record in threshold_set.values],
            "attainability_status": [
                None if record.attainability_status is None else record.attainability_status.value
                for record in threshold_set.values
            ],
            "policy_id": [threshold_set.policy_id.value] * len(threshold_set.values),
            "target_quantile": [threshold_set.target_quantile.value] * len(threshold_set.values),
        },
        schema_overrides={
            "effective_lambda": pl.Float64,
            "cluster_label": pl.Int64,
            "finite_sample_rank": pl.Int64,
            "attainability_status": pl.String,
        },
    )


def empty_threshold_frame() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "client_id": pl.String,
            "threshold": pl.Float64,
            "owner_kind": pl.String,
            "effective_lambda": pl.Float64,
            "cluster_label": pl.Int64,
            "finite_sample_rank": pl.Int64,
            "attainability_status": pl.String,
            "policy_id": pl.String,
            "target_quantile": pl.Float64,
        }
    )


def diagnostics_to_json(diagnostics: object) -> bytes:
    if diagnostics is None:
        return b"{}"
    if isinstance(diagnostics, MatchedExceedanceDiagnostics):
        payload = {
            "selected_coefficient": diagnostics.selected_coefficient,
            "candidate_grid": {
                "minimum": diagnostics.candidate_grid_minimum,
                "maximum": diagnostics.candidate_grid_maximum,
                "step": diagnostics.candidate_grid_step,
            },
            "pooled_mean": diagnostics.pooled_mean,
            "pooled_standard_deviation": diagnostics.pooled_standard_deviation,
            "achieved_exceedance": {str(k): v for k, v in diagnostics.achieved_exceedance},
            "tie_set": list(diagnostics.tie_set),
        }
    else:
        payload = {"note": "diagnostics_present"}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8")
