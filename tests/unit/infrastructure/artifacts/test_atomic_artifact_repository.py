"""Artifact transaction tests for atomic commit and verified reads."""

from pathlib import Path

from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactParent,
    BytesPayload,
    FilePayload,
)
from datp_core.domain.fingerprints import compute_execution_fingerprint, compute_scientific_fingerprint
from datp_core.domain.identifiers import ArtifactId
from datp_core.infrastructure.artifacts.atomic_commit import (
    AtomicArtifactRepository,
    commit_artifact_atomically,
    inspect_committed_artifact,
    read_committed_artifact,
)


def _request() -> ArtifactCommitRequest:
    scientific = compute_scientific_fingerprint({"experiment": "test"})
    return ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=ArtifactKey(artifact_id=ArtifactId("artifact"), kind=ArtifactKind.REPORT),
            artifact_format=ArtifactFormat.TEXT,
            scientific_fingerprint=scientific,
            execution_fingerprint=compute_execution_fingerprint({"scientific": scientific}),
            relative_path="reports/artifact",
            parents=(),
            schema_version=1,
            creation_timestamp=1.0,
            environment_identity="test",
        ),
        payload=BytesPayload(payload_bytes=b"verified payload"),
    )


def test_committed_artifact_is_read_only_after_checksum_verification(tmp_path: Path) -> None:
    assert commit_artifact_atomically(_request(), tmp_path, lock_timeout=1.0).success
    read = read_committed_artifact("reports/artifact", tmp_path)
    assert read.found
    assert read.payload_bytes == b"verified payload"


def test_corrupt_payload_is_not_returned(tmp_path: Path) -> None:
    assert commit_artifact_atomically(_request(), tmp_path, lock_timeout=1.0).success
    (tmp_path / "reports/artifact/payload.text").write_bytes(b"corrupt")
    assert not read_committed_artifact("reports/artifact", tmp_path).found


def test_repository_reuses_only_a_matching_frozen_artifact(tmp_path: Path) -> None:
    request = _request()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(request).success
    decision = repository.assess_reuse(
        request.metadata.relative_path,
        request.metadata.artifact_key,
        request.metadata.scientific_fingerprint,
        request.metadata.execution_fingerprint,
    )
    assert decision.can_reuse
    assert decision.existing_manifest is not None


def test_artifact_declaring_itself_as_its_own_parent_is_rejected(tmp_path: Path) -> None:
    request = _request()
    self_referential = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=request.metadata.artifact_key,
            artifact_format=request.metadata.artifact_format,
            scientific_fingerprint=request.metadata.scientific_fingerprint,
            execution_fingerprint=request.metadata.execution_fingerprint,
            relative_path=request.metadata.relative_path,
            parents=(
                ArtifactParent(
                    parent_key=request.metadata.artifact_key,
                    scientific_fingerprint=request.metadata.scientific_fingerprint,
                ),
            ),
            schema_version=request.metadata.schema_version,
            creation_timestamp=request.metadata.creation_timestamp,
            environment_identity=request.metadata.environment_identity,
        ),
        payload=BytesPayload(payload_bytes=b"verified payload"),
    )
    result = commit_artifact_atomically(self_referential, tmp_path, lock_timeout=1.0)
    assert not result.success
    assert result.error_message is not None
    assert "own parent" in result.error_message


def test_artifact_declaring_duplicate_parent_lineage_is_rejected(tmp_path: Path) -> None:
    request = _request()
    duplicate_parent = ArtifactKey(artifact_id=ArtifactId("some-parent"), kind=ArtifactKind.MATERIALIZED_DATASET)
    parent_entry = ArtifactParent(
        parent_key=duplicate_parent, scientific_fingerprint=request.metadata.scientific_fingerprint
    )
    with_duplicates = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=request.metadata.artifact_key,
            artifact_format=request.metadata.artifact_format,
            scientific_fingerprint=request.metadata.scientific_fingerprint,
            execution_fingerprint=request.metadata.execution_fingerprint,
            relative_path=request.metadata.relative_path,
            parents=(parent_entry, parent_entry),
            schema_version=request.metadata.schema_version,
            creation_timestamp=request.metadata.creation_timestamp,
            environment_identity=request.metadata.environment_identity,
        ),
        payload=BytesPayload(payload_bytes=b"verified payload"),
    )
    result = commit_artifact_atomically(with_duplicates, tmp_path, lock_timeout=1.0)
    assert not result.success
    assert result.error_message is not None
    assert "duplicate parent" in result.error_message


def test_file_commit_copies_and_verifies_a_staged_payload_without_in_memory_payload(tmp_path: Path) -> None:
    source = tmp_path / "staged.parquet"
    source.write_bytes(b"streamed payload" * 1000)
    scientific = compute_scientific_fingerprint({"experiment": "file"})
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=ArtifactKey(artifact_id=ArtifactId("file-artifact"), kind=ArtifactKind.MATERIALIZED_DATASET),
            artifact_format=ArtifactFormat.PARQUET,
            scientific_fingerprint=scientific,
            execution_fingerprint=compute_execution_fingerprint({"scientific": scientific}),
            relative_path="datasets/file-artifact",
            parents=(),
            schema_version=1,
            creation_timestamp=1.0,
            environment_identity="test",
        ),
        payload=FilePayload(source_file=str(source)),
    )
    assert commit_artifact_atomically(request, tmp_path / "artifacts", lock_timeout=1.0).success
    inspected = inspect_committed_artifact("datasets/file-artifact", tmp_path / "artifacts")
    assert inspected.found
    assert inspected.payload_bytes is None
