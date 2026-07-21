"""Artifact transaction tests for atomic commit and verified reads."""

from pathlib import Path

from datp_core.domain.artifacts import (
    ArtifactCommitRequest,
    ArtifactFileCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactParent,
)
from datp_core.domain.fingerprints import compute_execution_fingerprint, compute_scientific_fingerprint
from datp_core.domain.identifiers import ArtifactId
from datp_core.infrastructure.artifacts.atomic_commit import (
    AtomicArtifactRepository,
    commit_artifact_atomically,
    commit_artifact_file_atomically,
    inspect_committed_artifact,
    read_committed_artifact,
)


def _request() -> ArtifactCommitRequest:
    scientific = compute_scientific_fingerprint({"experiment": "test"})
    return ArtifactCommitRequest(
        artifact_key=ArtifactKey(artifact_id=ArtifactId("artifact"), kind=ArtifactKind.REPORT),
        artifact_format=ArtifactFormat.TEXT,
        scientific_fingerprint=scientific,
        execution_fingerprint=compute_execution_fingerprint({"scientific": scientific}),
        payload_bytes=b"verified payload",
        relative_path="reports/artifact",
        parents=(),
        schema_version=1,
        creation_timestamp=1.0,
        environment_identity="test",
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
        request.relative_path, request.artifact_key, request.scientific_fingerprint, request.execution_fingerprint
    )
    assert decision.can_reuse
    assert decision.existing_manifest is not None


def test_artifact_declaring_itself_as_its_own_parent_is_rejected(tmp_path: Path) -> None:
    request = _request()
    self_referential = ArtifactCommitRequest(
        artifact_key=request.artifact_key,
        artifact_format=request.artifact_format,
        scientific_fingerprint=request.scientific_fingerprint,
        execution_fingerprint=request.execution_fingerprint,
        payload_bytes=request.payload_bytes,
        relative_path=request.relative_path,
        parents=(
            ArtifactParent(parent_key=request.artifact_key, scientific_fingerprint=request.scientific_fingerprint),
        ),
        schema_version=request.schema_version,
        creation_timestamp=request.creation_timestamp,
        environment_identity=request.environment_identity,
    )
    result = commit_artifact_atomically(self_referential, tmp_path, lock_timeout=1.0)
    assert not result.success
    assert result.error_message is not None
    assert "own parent" in result.error_message


def test_artifact_declaring_duplicate_parent_lineage_is_rejected(tmp_path: Path) -> None:
    request = _request()
    duplicate_parent = ArtifactKey(artifact_id=ArtifactId("some-parent"), kind=ArtifactKind.MATERIALIZED_DATASET)
    parent_entry = ArtifactParent(parent_key=duplicate_parent, scientific_fingerprint=request.scientific_fingerprint)
    with_duplicates = ArtifactCommitRequest(
        artifact_key=request.artifact_key,
        artifact_format=request.artifact_format,
        scientific_fingerprint=request.scientific_fingerprint,
        execution_fingerprint=request.execution_fingerprint,
        payload_bytes=request.payload_bytes,
        relative_path=request.relative_path,
        parents=(parent_entry, parent_entry),
        schema_version=request.schema_version,
        creation_timestamp=request.creation_timestamp,
        environment_identity=request.environment_identity,
    )
    result = commit_artifact_atomically(with_duplicates, tmp_path, lock_timeout=1.0)
    assert not result.success
    assert result.error_message is not None
    assert "duplicate parent" in result.error_message


def test_file_commit_copies_and_verifies_a_staged_payload_without_in_memory_payload(tmp_path: Path) -> None:
    source = tmp_path / "staged.parquet"
    source.write_bytes(b"streamed payload" * 1000)
    scientific = compute_scientific_fingerprint({"experiment": "file"})
    request = ArtifactFileCommitRequest(
        artifact_key=ArtifactKey(artifact_id=ArtifactId("file-artifact"), kind=ArtifactKind.MATERIALIZED_DATASET),
        artifact_format=ArtifactFormat.PARQUET,
        scientific_fingerprint=scientific,
        execution_fingerprint=compute_execution_fingerprint({"scientific": scientific}),
        source_file=str(source),
        relative_path="datasets/file-artifact",
        parents=(),
        schema_version=1,
        creation_timestamp=1.0,
        environment_identity="test",
    )
    assert commit_artifact_file_atomically(request, tmp_path / "artifacts", lock_timeout=1.0).success
    inspected = inspect_committed_artifact("datasets/file-artifact", tmp_path / "artifacts")
    assert inspected.found
    assert inspected.payload_bytes is None
