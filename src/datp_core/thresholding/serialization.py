"""Threshold frame serialization and diagnostics JSON encoding."""

from __future__ import annotations

import json

import polars as pl

from datp_core.core.identifiers import ClientId, PopulationId
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    CalibrationFallbackDiagnostics,
    CalibrationSamplingDiagnostics,
    ClusterDiagnostics,
    ConformalDiagnostics,
    FederatedFixedDiagnostics,
    FederatedMatchedDiagnostics,
    ShrinkageDiagnostics,
    ThresholdDiagnostics,
    ThresholdingError,
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
            "client_id": [rec.client_id.value for rec in threshold_set.values],
            "threshold": [float(rec.threshold) for rec in threshold_set.values],
            "policy_kind": [rec.policy_kind.value for rec in threshold_set.values],
            "scope": [rec.scope.value for rec in threshold_set.values],
            "effective_lambda": [rec.effective_lambda for rec in threshold_set.values],
            "cluster_label": [rec.cluster_label for rec in threshold_set.values],
            "finite_sample_rank": [rec.finite_sample_rank for rec in threshold_set.values],
            "policy_id": [threshold_set.policy_id.value] * len(threshold_set.values),
            "target_quantile": [threshold_set.target_quantile.value] * len(threshold_set.values),
        },
        schema_overrides={
            "effective_lambda": pl.Float64,
            "cluster_label": pl.Int64,
            "finite_sample_rank": pl.Int64,
        },
    )


def empty_threshold_frame() -> pl.DataFrame:
    """Create an empty threshold frame with the canonical schema."""
    return pl.DataFrame(
        schema={
            "client_id": pl.String,
            "threshold": pl.Float64,
            "policy_kind": pl.String,
            "scope": pl.String,
            "effective_lambda": pl.Float64,
            "cluster_label": pl.Int64,
            "finite_sample_rank": pl.Int64,
            "policy_id": pl.String,
            "target_quantile": pl.Float64,
        }
    )


def diagnostics_to_json(diagnostics: ThresholdDiagnostics | None) -> bytes:
    """Serialize diagnostics losslessly to JSON bytes."""
    if diagnostics is None:
        return b"{}"
    if isinstance(diagnostics, FederatedMatchedDiagnostics):
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
    elif isinstance(diagnostics, FederatedFixedDiagnostics):
        payload = {
            "coefficient": diagnostics.coefficient,
            "pooled_mean": diagnostics.pooled_mean,
            "pooled_standard_deviation": diagnostics.pooled_standard_deviation,
        }
    elif isinstance(diagnostics, ClusterDiagnostics):
        payload = {
            "cluster_count": diagnostics.cluster_count,
            "cluster_labels": [{"client_id": cid, "label": label} for cid, label in diagnostics.cluster_labels],
            "aggregation": diagnostics.aggregation.value,
            "fingerprint_features": list(diagnostics.fingerprint_features),
        }
    elif isinstance(diagnostics, ConformalDiagnostics):
        payload = {
            "coverage_alpha": diagnostics.coverage_alpha,
            "ranks": [{"client_id": cid, "rank": rank} for cid, rank in diagnostics.ranks],
        }
    elif isinstance(diagnostics, ShrinkageDiagnostics):
        payload = {
            "effective_lambdas": {cid: lam for cid, lam in diagnostics.effective_lambdas},
        }
    elif isinstance(diagnostics, CalibrationFallbackDiagnostics):
        payload = {
            "n_half": diagnostics.n_half,
            "effective_lambdas": {cid: lam for cid, lam in diagnostics.effective_lambdas},
            "calibration_counts": {cid: count for cid, count in diagnostics.calibration_counts},
        }
    elif isinstance(diagnostics, CalibrationSamplingDiagnostics):
        payload = {
            "requested_count": diagnostics.requested_count,
            "replicate": diagnostics.replicate,
            "client_counts": {cid: count for cid, count in diagnostics.client_counts},
        }
    else:
        raise ThresholdingError(f"Unknown diagnostics type: {type(diagnostics).__name__}")
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8")
