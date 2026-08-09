"""Deterministic Parquet persistence for typed artifact repositories."""

from pathlib import Path

import polars as pl

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
)
from datp_core.core.numeric import RowCount


def write_frame(frame: pl.DataFrame, destination: Path) -> tuple[Checksum, RowCount]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(destination)
    return Checksum.from_file(destination), RowCount(frame.height)


def read_frame(
    path: Path,
    *,
    expected_checksum: Checksum | None = None,
    expected_row_count: RowCount | None = None,
) -> pl.DataFrame:
    if not path.is_file():
        raise ArtifactIntegrityError(ErrorMessage(f"Parquet artifact is missing: {path}"))
    if expected_checksum is not None and Checksum.from_file(path) != expected_checksum:
        raise ArtifactIntegrityError(ErrorMessage(f"Parquet artifact checksum mismatch: {path}"))
    frame = pl.read_parquet(path)
    if expected_row_count is not None and frame.height != expected_row_count.value:
        raise ArtifactIntegrityError(ErrorMessage(f"Parquet artifact row count mismatch: {path}"))
    return frame
