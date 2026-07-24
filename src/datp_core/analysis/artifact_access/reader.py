"""Run-relative artifact reads shared by every analysis capability: path construction, the
missing-payload check, and raw Parquet decoding. Frame-contract validation stays with the caller,
since whether a decoded frame is validated against its base contract is a scientific decision (for
example, cluster-label columns are deliberately read without contract validation) rather than an
artifact-access concern.
"""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.models import ArtifactRepository
from datp_core.core.identifiers import JobId, RunId


def read_artifact_bytes(repository: ArtifactRepository, run_id: RunId, job_id: JobId, *, missing_message: str) -> bytes:
    artifact = repository.read(f"runs/{run_id.value}/{job_id.value}")
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError(missing_message)
    return artifact.payload_bytes


def read_parquet_frame(
    repository: ArtifactRepository, run_id: RunId, job_id: JobId, *, missing_message: str
) -> pl.DataFrame:
    return pl.read_parquet(BytesIO(read_artifact_bytes(repository, run_id, job_id, missing_message=missing_message)))


__all__ = ["read_artifact_bytes", "read_parquet_frame"]
