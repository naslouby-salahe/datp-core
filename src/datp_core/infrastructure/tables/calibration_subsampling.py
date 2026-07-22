"""Deterministic, nested benign-calibration subsampling for boundary experiments."""

from __future__ import annotations

from hashlib import blake2b

import numpy as np
import polars as pl


def subsample_calibration_scores(
    scores: pl.DataFrame,
    *,
    requested_sample_count: int,
    training_seed: int,
    selection_seed: int,
    replicate: int,
    namespace_key: str,
    digest_bytes: int,
) -> pl.DataFrame:
    """Return each eligible client's deterministic prefix of its replicate permutation.

    The permutation is independent of requested size, making smaller windows exact prefixes
    of larger windows for the same seed, client, and replicate.
    """
    if requested_sample_count < 1 or replicate < 0 or digest_bytes < 1 or not namespace_key:
        raise ValueError(
            "Calibration subsampling requires positive size, namespace digest, and a non-negative replicate"
        )
    required = {"client_id", "source_path", "source_row_index", "score"}
    if missing := required - set(scores.columns):
        raise ValueError(f"Calibration scores lack deterministic subsampling columns: {', '.join(sorted(missing))}")
    ordered = scores.sort("client_id", "source_path", "source_row_index")
    samples: list[pl.DataFrame] = []
    for client, client_scores in ordered.group_by("client_id", maintain_order=True):
        if client_scores.height < requested_sample_count:
            continue
        seed = _subsample_seed(
            namespace_key,
            digest_bytes,
            client_id=str(client[0]),
            training_seed=training_seed,
            selection_seed=selection_seed,
            replicate=replicate,
        )
        positions = np.random.default_rng(seed).permutation(client_scores.height)[:requested_sample_count]
        samples.append(client_scores.gather(pl.Series(positions)).sort("source_path", "source_row_index"))
    if not samples:
        return ordered.head(0)
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
    components = (
        ("client_identifier", client_id),
        ("replicate_index", replicate),
        ("selection_seed", selection_seed),
        ("training_seed", training_seed),
    )
    encoded = "|".join((key, *(f"{name}={value}" for name, value in components))).encode("utf-8")
    return int.from_bytes(blake2b(encoded, digest_size=digest_bytes).digest(), "big") % (2**32)
