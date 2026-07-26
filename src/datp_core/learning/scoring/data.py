"""Data loading utilities for reconstruction scoring: benign client tensors, input/output frames."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp_core.data.contracts.enums import SplitMembership

_SCORE_IDENTITY_COLUMNS = ("source_path", "source_row_index", "client_id", "split", "is_attack")


def load_benign_client_tensors(
    path: Path, split: str, feature_columns: tuple[str, ...]
) -> tuple[tuple[str, torch.Tensor], ...]:
    """Load configured benign rows for one authorized split, ordered by client."""
    if not feature_columns:
        raise ValueError("Training requires configured model feature columns")
    frame = pl.read_parquet(path, columns=["split", "client_id", "is_attack", *feature_columns])
    required = {"split", "client_id", "is_attack", *feature_columns}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Materialized payload lacks training columns: {', '.join(missing)}")
    selected = frame.filter((pl.col("split") == split) & ~pl.col("is_attack")).select("client_id", *feature_columns)
    if selected.is_empty():
        raise ValueError(f"Materialized payload has no benign {split} rows")
    tensors: list[tuple[str, torch.Tensor]] = []
    for client_id, client_rows in selected.group_by("client_id", maintain_order=True):
        values = client_rows.select(*feature_columns).to_numpy()
        if not np.isfinite(values).all():
            raise ValueError(f"Benign {split} rows for client '{client_id[0]}' contain non-finite feature values")
        tensors.append((str(client_id[0]), torch.tensor(values, dtype=torch.float32)))
    return tuple(sorted(tensors, key=lambda item: item[0]))


def materialized_feature_columns(path: Path) -> tuple[str, ...]:
    """Infer model feature columns from a materialized Parquet file's schema.

    Shared by the training handler (materialization has no configured ``field_schema.model_features``
    fallback path) and the score-generation stage handler.
    """
    metadata_columns = {"split", "client_id", "source_path", "source_row_index", "is_attack", "chronology_key"}
    columns = tuple(column for column in pl.read_parquet(path, n_rows=0).columns if column not in metadata_columns)
    if not columns:
        raise ValueError("Materialized dataset has no model feature columns")
    return columns


def _score_input_frame(path: Path, *, split: str, feature_columns: tuple[str, ...]) -> pl.DataFrame:
    """Load and validate the input frame for one scoring split."""
    allowed_splits = {
        SplitMembership.CALIBRATION.value,
        SplitMembership.TEST.value,
        SplitMembership.HISTORICAL_CALIBRATION.value,
        SplitMembership.FUTURE_RECALIBRATION.value,
        SplitMembership.FUTURE_EVALUATION.value,
    }
    if split not in allowed_splits:
        raise ValueError(f"Scoring does not authorize split '{split}'")
    frame = pl.read_parquet(path, columns=[*_SCORE_IDENTITY_COLUMNS, *feature_columns])
    selected = frame.filter(pl.col("split") == split)
    if selected.is_empty():
        raise ValueError(f"Materialized payload has no {split} rows to score")
    if split in {"calibration", "historical_calibration", "future_recalibration"} and selected["is_attack"].any():
        raise ValueError("Calibration scoring must not include attack rows")
    if selected.select(pl.struct("source_path", "source_row_index").is_duplicated().any()).item():
        raise ValueError("Score input contains duplicate row identities")
    if not np.isfinite(selected.select(*feature_columns).to_numpy()).all():
        raise ValueError("Score input contains non-finite feature values")
    return selected


def _score_output_frame(selected: pl.DataFrame, scores: np.ndarray | None) -> pl.DataFrame:
    """Produce the validated score output frame from an input frame and score array."""
    if scores is not None:
        selected = selected.with_columns(pl.Series("score", scores, dtype=pl.Float64))
    scores = selected["score"].to_numpy()
    if not np.isfinite(scores).all() or (scores < 0.0).any():
        raise ValueError("Model produced non-finite or negative reconstruction scores")
    return (
        selected.select(*_SCORE_IDENTITY_COLUMNS, "score")
        .with_columns(
            pl.col("score").cast(pl.Float64),
            pl.col("is_attack").cast(pl.Int64).alias("label"),
        )
        .drop("is_attack")
    )
