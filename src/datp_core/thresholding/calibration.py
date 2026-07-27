"""Deterministic, nested benign-calibration subsampling."""

from __future__ import annotations

import numpy as np
import polars as pl

from datp_core.core.seeding import derive_seed
from datp_core.thresholding.models import (
    CalibrationSampleRequest,
    InsufficientCalibrationError,
)


def subsample_calibration_scores(
    scores: pl.DataFrame,
    *,
    request: CalibrationSampleRequest,
) -> pl.DataFrame:
    """Deterministically subsample calibration scores without replacement.

    Preserves deterministic client ordering and source ordering.
    Silently drops clients with fewer than `request.requested_sample_count` rows;
    raises InsufficientCalibrationError when no client qualifies.
    """
    required = {"client_id", "source_path", "source_row_index", "score"}
    if missing := required - set(scores.columns):
        raise ValueError(f"Calibration scores lack required columns: {', '.join(sorted(missing))}")
    ordered = scores.sort("client_id", "source_path", "source_row_index")
    samples: list[pl.DataFrame] = []
    for client, client_scores in ordered.group_by("client_id", maintain_order=True):
        if client_scores.height < request.requested_sample_count:
            continue
        seed = _subsample_seed(
            key=request.namespace_key,
            digest_bytes=request.digest_bytes,
            client_id=str(client[0]),
            training_seed=request.training_seed,
            selection_seed=request.selection_seed,
            replicate=request.replicate,
        )
        positions = np.random.default_rng(seed).permutation(client_scores.height)[: request.requested_sample_count]
        samples.append(client_scores.gather(pl.Series(positions)).sort("source_path", "source_row_index"))
    if not samples:
        raise InsufficientCalibrationError(
            f"No client has at least {request.requested_sample_count} calibration rows "
            f"for replicate {request.replicate}"
        )
    return pl.concat(samples).sort("client_id", "source_path", "source_row_index")


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
