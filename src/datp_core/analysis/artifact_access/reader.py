"""Direct current-run file reads shared by analysis capabilities."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.errors import ArtifactFileMissingError
from datp_core.artifacts.store import ArtifactStore


def read_artifact_bytes(store: ArtifactStore, relative_path: str, *, missing_message: str) -> bytes:
    try:
        return store.read_bytes(relative_path)
    except ArtifactFileMissingError as exc:
        raise ValueError(missing_message) from exc


def read_parquet_frame(store: ArtifactStore, relative_path: str, *, missing_message: str) -> pl.DataFrame:
    return pl.read_parquet(BytesIO(read_artifact_bytes(store, relative_path, missing_message=missing_message)))


__all__ = ["read_artifact_bytes", "read_parquet_frame"]
