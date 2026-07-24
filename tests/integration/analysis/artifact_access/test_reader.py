"""Run-relative artifact reads against a real committed repository: found, missing, and decoded
Parquet cases."""

from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import polars as pl
import pytest

from datp_core.analysis.artifact_access.reader import read_artifact_bytes, read_parquet_frame
from datp_core.artifacts.codecs.manifest import CURRENT_ARTIFACT_SCHEMA_VERSION
from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.payloads import ArtifactCommitMetadata, ArtifactCommitRequest, BytesPayload
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.core.hashing import Fingerprint
from datp_core.core.identifiers import ExperimentId
from datp_core.pipeline.stages.node_key import StageNodeKey
from datp_core.pipeline.stages.enums import StageKind

_FINGERPRINT = Fingerprint("a" * 64)


def _commit(
    repository: AtomicArtifactRepository, *, relative_path: str, artifact_format: ArtifactFormat, payload: bytes
) -> None:
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=ArtifactKey(node_key=StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT), kind=ArtifactKind.CLIENT_METRICS),
            artifact_format=artifact_format,
            scientific_fingerprint=_FINGERPRINT,
            execution_fingerprint=_FINGERPRINT,
            relative_path=relative_path,
            parents=(),
            schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
            creation_timestamp=time.time(),
            environment_identity="test",
        ),
        payload=BytesPayload(payload_bytes=payload),
    )
    result = repository.commit(request)
    assert result.success, result.error_message


def test_read_artifact_bytes_returns_the_committed_payload(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    _commit(repository, relative_path="experiments/test/preflight", artifact_format=ArtifactFormat.JSON, payload=b'{"a": 1}')

    result = read_artifact_bytes(repository, ExperimentId("test"), StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT), missing_message="should not be raised")

    assert result == b'{"a": 1}'


def test_read_artifact_bytes_raises_the_supplied_message_when_the_artifact_is_missing(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)

    with pytest.raises(ValueError, match="custom missing-artifact message"):
        read_artifact_bytes(repository, ExperimentId("test"), StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT), missing_message="custom missing-artifact message")


def test_read_parquet_frame_decodes_the_committed_bytes(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    frame = pl.DataFrame({"client_id": ["a", "b"], "value": [1.0, 2.0]})
    buffer = BytesIO()
    frame.write_parquet(buffer)
    _commit(repository, relative_path="experiments/test/preflight", artifact_format=ArtifactFormat.PARQUET, payload=buffer.getvalue())

    decoded = read_parquet_frame(repository, ExperimentId("test"), StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT), missing_message="should not be raised")

    assert decoded.equals(frame)


def test_read_parquet_frame_raises_when_the_artifact_is_missing(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)

    with pytest.raises(ValueError, match="frame is unavailable"):
        read_parquet_frame(repository, ExperimentId("test"), StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT), missing_message="frame is unavailable")
