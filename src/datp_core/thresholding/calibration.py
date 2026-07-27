"""Deterministic, nested benign-calibration subsampling."""

from __future__ import annotations

import numpy as np
import polars as pl

from datp_core.core.identifiers import ClientId
from datp_core.core.seeding import derive_seed
from datp_core.thresholding.models import (
    CalibrationSampleRequest,
    CalibrationSampleResult,
    InsufficientCalibrationError,
)

_CALIBRATION_COLUMNS: frozenset[str] = frozenset({"client_id", "source_path", "source_row_index", "score"})


def subsample_calibration_scores(
    scores: pl.DataFrame,
    *,
    request: CalibrationSampleRequest,
) -> CalibrationSampleResult:
    """Deterministically subsample calibration scores without replacement.

    Args:
        scores: Calibration score frame with canonical columns.
        request: Validated subsample request.

    Returns:
        CalibrationSampleResult with sampled scores per client.

    Raises:
        InsufficientCalibrationError: When any required client lacks enough rows.
    """
    missing = _CALIBRATION_COLUMNS - set(scores.columns)
    if missing:
        raise ValueError(f"Calibration scores lack required columns: {', '.join(sorted(missing))}")
    ordered = scores.sort("client_id", "source_path", "source_row_index")

    # Collect all required client IDs
    required_clients: set[str] = set()
    for client_id in ordered["client_id"].unique().to_list():
        required_clients.add(str(client_id))

    # Check every required client has enough rows
    insufficient: list[tuple[str, int, int]] = []
    samples: list[pl.DataFrame] = []
    for client, client_scores in ordered.group_by("client_id", maintain_order=True):
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
        samples.append(client_scores.gather(pl.Series(positions)).sort("source_path", "source_row_index"))

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

    result_frame = pl.concat(samples).sort("client_id", "source_path", "source_row_index")
    sampled_scores: list = []
    for client_id_str, rows in result_frame.group_by("client_id", maintain_order=True):
        sampled_scores.append(
            (
                ClientId(str(client_id_str[0])),
                tuple(float(v) for v in rows["score"].to_list()),
            )
        )

    return CalibrationSampleResult(
        sampled_scores=tuple(sampled_scores),
        sample_count=request.requested_sample_count,
        replicate=request.replicate,
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
