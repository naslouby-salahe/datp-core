"""Deterministic, nested benign-calibration subsampling."""

from __future__ import annotations

import numpy as np
import polars as pl

from datp_core.artifacts.schemas.columns import ScoreColumn
from datp_core.core.seeding import derive_seed
from datp_core.thresholding.models import (
    CalibrationSampleRequest,
    InsufficientCalibrationError,
    ThresholdConfigurationError,
)


def subsample_calibration_scores(
    scores: pl.DataFrame,
    *,
    request: CalibrationSampleRequest,
) -> pl.DataFrame:
    """Deterministically subsample calibration scores without replacement.

    Args:
        scores: Calibration score frame with canonical columns.
        request: Validated subsample request.

    Returns:
        Sampled calibration score frame with canonical columns.

    Raises:
        InsufficientCalibrationError: When any required client lacks enough rows.
    """
    expected_calibration_columns: frozenset[str] = frozenset(
        {
            ScoreColumn.CLIENT_ID.value,
            ScoreColumn.SOURCE_PATH.value,
            ScoreColumn.SOURCE_ROW_INDEX.value,
            ScoreColumn.SCORE.value,
        }
    )
    missing = expected_calibration_columns - set(scores.columns)
    if missing:
        raise ThresholdConfigurationError(f"Calibration scores lack required columns: {', '.join(sorted(missing))}")
    ordered = scores.sort(
        ScoreColumn.CLIENT_ID.value, ScoreColumn.SOURCE_PATH.value, ScoreColumn.SOURCE_ROW_INDEX.value
    )

    # Check every required client has enough rows
    insufficient: list[tuple[str, int, int]] = []
    samples: list[pl.DataFrame] = []
    for client, client_scores in ordered.group_by(ScoreColumn.CLIENT_ID.value, maintain_order=True):
        client_str = str(client[0])
        available = client_scores.height
        if available < request.requested_sample_count:
            insufficient.append((client_str, available, request.requested_sample_count))
            continue
        seed = _subsample_seed(
            key=request.namespace_key,
            digest_bytes=request.digest_bytes,
            client_id=client_str,
            training_seed=request.training_seed,
            selection_seed=request.selection_seed,
            replicate=request.replicate,
        )
        positions = np.random.default_rng(seed).permutation(available)[: request.requested_sample_count]
        samples.append(
            client_scores.gather(pl.Series(positions)).sort(
                ScoreColumn.SOURCE_PATH.value, ScoreColumn.SOURCE_ROW_INDEX.value
            )
        )

    if insufficient:
        detail = "; ".join(f"client '{cid}' has {avail} rows, needs {need}" for cid, avail, need in insufficient)
        raise InsufficientCalibrationError(
            f"Calibration subsample of size {request.requested_sample_count} "
            f"is not attainable for {len(insufficient)} client(s): {detail}"
        )

    if not samples:
        raise InsufficientCalibrationError(
            f"No client has at least {request.requested_sample_count} calibration rows "
            f"for replicate {request.replicate}"
        )

    return pl.concat(samples).sort(
        ScoreColumn.CLIENT_ID.value, ScoreColumn.SOURCE_PATH.value, ScoreColumn.SOURCE_ROW_INDEX.value
    )


def _subsample_seed(
    key: str,
    digest_bytes: int,
    *,
    client_id: str,
    training_seed: int,
    selection_seed: int,
    replicate: int,
) -> int:
    return derive_seed(
        key,
        digest_bytes,
        (
            ("client_identifier", client_id),
            ("replicate_index", replicate),
            ("selection_seed", selection_seed),
            ("training_seed", training_seed),
        ),
    )
