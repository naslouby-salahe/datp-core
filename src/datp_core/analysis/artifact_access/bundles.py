"""Typed multi-artifact bundles reused by more than one analysis capability."""

from __future__ import annotations

import polars as pl

from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore


def threshold_and_calibration_frame(
    *,
    store: ArtifactStore,
    threshold_path: str,
    calibration_score_path: str,
    missing_message: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    threshold = validate_threshold_frame(read_parquet_frame(store, threshold_path, missing_message=missing_message))
    calibration = validate_calibration_score_frame(
        read_parquet_frame(store, calibration_score_path, missing_message=missing_message)
    )
    return threshold, calibration


__all__ = ["threshold_and_calibration_frame"]
