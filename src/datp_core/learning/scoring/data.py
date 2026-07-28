"""In-memory materialization validation for training and scoring."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
import polars as pl
import torch

from datp_core.data.contracts.enums import SplitMembership
from datp_core.learning.contracts.enums import PrecisionKind
from datp_core.learning.model.runtime import precision_to_dtype
from datp_core.learning.training.engine import ClientTensor, LearningDataError

_SCORE_IDENTITY_COLUMNS = (
    "source_path",
    "source_row_index",
    "client_id",
    "split",
    "is_attack",
)


@dataclass(frozen=True, slots=True)
class MaterializedFrame:
    frame: pl.DataFrame
    feature_columns: tuple[str, ...]


def read_materialization(payload: bytes, feature_columns: tuple[str, ...]) -> MaterializedFrame:
    if not feature_columns:
        raise LearningDataError("Materialization requires explicit model feature columns")
    frame = pl.read_parquet(BytesIO(payload))
    required_columns = (*_SCORE_IDENTITY_COLUMNS, *feature_columns)
    missing = tuple(column for column in required_columns if column not in frame.columns)
    if missing:
        raise LearningDataError(
            f"Materialization lacks required columns: {', '.join(missing)}"
        )
    if frame.select(pl.struct("source_path", "source_row_index").is_duplicated().any()).item():
        raise LearningDataError("Materialization contains duplicate immutable row identities")
    if not np.isfinite(frame.select(*feature_columns).to_numpy()).all():
        raise LearningDataError("Materialization contains non-finite model feature values")
    return MaterializedFrame(frame=frame, feature_columns=feature_columns)


def benign_client_tensors(
    materialization: MaterializedFrame,
    split: SplitMembership,
    precision: PrecisionKind,
) -> tuple[ClientTensor, ...]:
    selected = materialization.frame.filter(
        (pl.col("split") == split.value) & ~pl.col("is_attack")
    ).select("client_id", *materialization.feature_columns)
    if selected.is_empty():
        raise LearningDataError(f"Materialization has no benign rows for split '{split.value}'")
    clients: list[ClientTensor] = []
    for key, rows in selected.group_by("client_id", maintain_order=True):
        client_id = str(key[0])
        values = rows.select(*materialization.feature_columns).to_numpy()
        clients.append(
            ClientTensor(
                client_id=client_id,
                tensor=torch.as_tensor(values, dtype=precision_to_dtype(precision), device="cpu"),
            )
        )
    return tuple(sorted(clients, key=lambda client: client.client_id))


def scoring_frame(
    materialization: MaterializedFrame,
    split: SplitMembership,
) -> pl.DataFrame:
    selected = materialization.frame.filter(pl.col("split") == split.value).select(
        *_SCORE_IDENTITY_COLUMNS,
        *materialization.feature_columns,
    )
    if selected.is_empty():
        raise LearningDataError(f"Materialization has no rows for scoring split '{split.value}'")
    calibration_splits = {
        SplitMembership.CALIBRATION,
        SplitMembership.HISTORICAL_CALIBRATION,
        SplitMembership.FUTURE_RECALIBRATION,
    }
    if split in calibration_splits and selected["is_attack"].any():
        raise LearningDataError("Calibration scoring must not include attack rows")
    return selected


def score_output_frame(selected: pl.DataFrame, scores: np.ndarray) -> pl.DataFrame:
    if len(scores) != selected.height:
        raise LearningDataError("Score count does not match the selected materialization rows")
    if not np.isfinite(scores).all() or (scores < 0.0).any():
        raise LearningDataError("Reconstruction scoring produced non-finite or negative values")
    return (
        selected.with_columns(pl.Series("score", scores, dtype=pl.Float64))
        .select(*_SCORE_IDENTITY_COLUMNS, "score")
        .with_columns(pl.col("is_attack").cast(pl.Int64).alias("label"))
        .drop("is_attack")
    )
