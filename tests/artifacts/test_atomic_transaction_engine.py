from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactCorruptionReason,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactParent,
    ArtifactReuseReason,
    BytesPayload,
    FilePayload,
)
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.artifacts.serialization import CURRENT_ARTIFACT_SCHEMA_VERSION, decode_manifest
from datp_core.configuration.fingerprints import compute_execution_fingerprint, compute_scientific_fingerprint
from datp_core.pipeline.identifiers import ArtifactId


def _metadata(**overrides: object) -> ArtifactCommitMetadata:
    scientific = compute_scientific_fingerprint({"experiment": "theme8"})
    defaults: dict[str, object] = {
        "artifact_key": ArtifactKey(artifact_id=ArtifactId("test-artifact"), kind=ArtifactKind.REPORT),
        "artifact_format": ArtifactFormat.TEXT,
        "scientific_fingerprint": scientific,
        "execution_fingerprint": compute_execution_fingerprint({"scientific": scientific}),
        "relative_path": "reports/test-artifact",
        "parents": (),
        "schema_version": CURRENT_ARTIFACT_SCHEMA_VERSION,
        "creation_timestamp": 1.0,
        "environment_identity": "test",
    }
    defaults.update(overrides)
    return ArtifactCommitMetadata(**defaults)  # type: ignore[arg-type]


def _bytes_request(payload_bytes: bytes = b"theme8 payload", **meta_overrides: object) -> ArtifactCommitRequest:
    return ArtifactCommitRequest(
        metadata=_metadata(**meta_overrides), payload=BytesPayload(payload_bytes=payload_bytes)
    )


def _file_request(source_file: str, **meta_overrides: object) -> ArtifactCommitRequest:
    return ArtifactCommitRequest(metadata=_metadata(**meta_overrides), payload=FilePayload(source_file=source_file))


def test_bytes_commit_succeeds_and_produces_correct_layout(tmp_path: Path) -> None:
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request())
    assert result.success
    assert result.manifest is not None

    target = tmp_path / "reports/test-artifact"
    assert target.is_dir()
    assert (target / "manifest.json").exists()
    assert (target / "payload.text").exists()


def test_file_commit_succeeds_and_copies_payload(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"staged file content")
    result = AtomicArtifactRepository(tmp_path / "artifacts", lock_timeout=1.0).commit(_file_request(str(source)))
    assert result.success
    target = tmp_path / "artifacts/reports/test-artifact"
    assert target.is_dir()
    assert (target / "payload.text").read_bytes() == b"staged file content"


def test_file_commit_leaves_source_file_intact(tmp_path: Path) -> None:
    """Staged-file commits copy the source, they do not move/consume it."""
    source = tmp_path / "keep_me.dat"
    source.write_bytes(b"original")
    result = AtomicArtifactRepository(tmp_path / "artifacts", lock_timeout=1.0).commit(_file_request(str(source)))
    assert result.success
    assert source.read_bytes() == b"original"


def test_existing_frozen_target_is_rejected_for_bytes(tmp_path: Path) -> None:
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repo.commit(_bytes_request()).success
    second = repo.commit(_bytes_request())
    assert not second.success
    assert second.error_message is not None
    assert "already exists" in second.error_message


def test_existing_frozen_target_is_rejected_for_file(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"content")
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repo.commit(_file_request(str(source))).success
    second = repo.commit(_file_request(str(source)))
    assert not second.success
    assert second.error_message is not None
    assert "already exists" in second.error_message


@pytest.mark.parametrize("bad_path", ["/absolute/path", "../escape", "sub/../../escape", "reports/../escape"])
def test_escaping_relative_path_is_rejected_for_bytes(bad_path: str, tmp_path: Path) -> None:
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request(relative_path=bad_path))
    assert not result.success
    assert result.error_message is not None
    assert "escapes" in result.error_message


@pytest.mark.parametrize("bad_path", ["/absolute/path", "../escape", "sub/../../escape", "reports/../escape"])
def test_escaping_relative_path_is_rejected_for_file(bad_path: str, tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"content")
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _file_request(str(source), relative_path=bad_path)
    )
    assert not result.success
    assert result.error_message is not None
    assert "escapes" in result.error_message


def test_missing_staged_source_is_rejected(tmp_path: Path) -> None:
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _file_request(str(tmp_path / "no_such_file.dat"))
    )
    assert not result.success
    assert result.error_message is not None
    assert "missing" in result.error_message


def test_directory_as_staged_source_is_rejected(tmp_path: Path) -> None:
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_file_request(str(dir_path)))
    assert not result.success
    assert result.error_message is not None
    assert "missing" in result.error_message


def test_self_parent_is_rejected_for_bytes(tmp_path: Path) -> None:
    key = ArtifactKey(artifact_id=ArtifactId("self"), kind=ArtifactKind.REPORT)
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _bytes_request(
            artifact_key=key,
            parents=(ArtifactParent(parent_key=key, scientific_fingerprint=_metadata().scientific_fingerprint),),
        )
    )
    assert not result.success
    assert result.error_message is not None
    assert "own parent" in result.error_message


def test_self_parent_is_rejected_for_file(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"content")
    key = ArtifactKey(artifact_id=ArtifactId("self"), kind=ArtifactKind.REPORT)
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _file_request(
            str(source),
            artifact_key=key,
            parents=(ArtifactParent(parent_key=key, scientific_fingerprint=_metadata().scientific_fingerprint),),
        )
    )
    assert not result.success
    assert result.error_message is not None
    assert "own parent" in result.error_message


def test_duplicate_parent_is_rejected_for_bytes(tmp_path: Path) -> None:
    dup_key = ArtifactKey(artifact_id=ArtifactId("dup"), kind=ArtifactKind.MATERIALIZED_DATASET)
    parent = ArtifactParent(parent_key=dup_key, scientific_fingerprint=_metadata().scientific_fingerprint)
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request(parents=(parent, parent)))
    assert not result.success
    assert result.error_message is not None
    assert "duplicate parent" in result.error_message


def test_duplicate_parent_is_rejected_for_file(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"content")
    dup_key = ArtifactKey(artifact_id=ArtifactId("dup"), kind=ArtifactKind.MATERIALIZED_DATASET)
    parent = ArtifactParent(parent_key=dup_key, scientific_fingerprint=_metadata().scientific_fingerprint)
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _file_request(str(source), parents=(parent, parent))
    )
    assert not result.success
    assert result.error_message is not None
    assert "duplicate parent" in result.error_message


def test_payload_checksum_is_stored_for_bytes(tmp_path: Path) -> None:
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request(b"checksum me"))
    assert result.success
    assert result.manifest is not None
    assert len(result.manifest.payload_checksum.value) == 64


def test_payload_checksum_is_stored_for_file(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"checksum me too")
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_file_request(str(source)))
    assert result.success
    assert result.manifest is not None
    assert len(result.manifest.payload_checksum.value) == 64


def test_byte_and_file_checksums_match_for_identical_content(tmp_path: Path) -> None:
    content = b"identical"
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    bytes_result = repo.commit(_bytes_request(content, relative_path="reports/bytes-path"))
    source = tmp_path / "identical.dat"
    source.write_bytes(content)
    file_result = repo.commit(_file_request(str(source), relative_path="reports/file-path"))
    assert bytes_result.manifest is not None
    assert file_result.manifest is not None
    assert bytes_result.manifest.payload_checksum == file_result.manifest.payload_checksum


def test_manifest_bytes_are_identical_for_equivalent_metadata(tmp_path: Path) -> None:
    """Manifest byte equality before/after for equivalent metadata."""
    content = b"manifest test"
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    repo.commit(_bytes_request(content, relative_path="reports/manifest-a"))
    repo.commit(_bytes_request(content, relative_path="reports/manifest-b"))

    manifest1_bytes = (tmp_path / "reports/manifest-a/manifest.json").read_bytes()
    manifest2_bytes = (tmp_path / "reports/manifest-b/manifest.json").read_bytes()
    assert manifest1_bytes != manifest2_bytes

    decoded1 = decode_manifest(manifest1_bytes)
    decoded2 = decode_manifest(manifest2_bytes)
    assert decoded1.payload_checksum == decoded2.payload_checksum
    assert decoded1.scientific_fingerprint == decoded2.scientific_fingerprint
    assert decoded1.execution_fingerprint == decoded2.execution_fingerprint
    assert decoded1.schema_version == decoded2.schema_version


def test_manifest_round_trips_all_fields(tmp_path: Path) -> None:
    scientific = compute_scientific_fingerprint({"experiment": "roundtrip"})
    key = ArtifactKey(artifact_id=ArtifactId("full-artifact"), kind=ArtifactKind.STATISTICAL_SUMMARY)
    parent_key = ArtifactKey(artifact_id=ArtifactId("parent-artifact"), kind=ArtifactKind.MATERIALIZED_DATASET)
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=key,
            artifact_format=ArtifactFormat.JSON,
            scientific_fingerprint=scientific,
            execution_fingerprint=compute_execution_fingerprint({"scientific": scientific}),
            relative_path="stats/full-artifact",
            parents=(ArtifactParent(parent_key=parent_key, scientific_fingerprint=scientific),),
            schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
            creation_timestamp=42.5,
            environment_identity="ci-test-runner",
        ),
        payload=BytesPayload(payload_bytes=b'{"metric": 0.95}'),
    )
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    result = repo.commit(request)
    assert result.success
    assert result.manifest is not None

    decoded = decode_manifest((tmp_path / "stats/full-artifact/manifest.json").read_bytes())
    assert decoded.artifact_key == key
    assert decoded.artifact_format == ArtifactFormat.JSON
    assert decoded.state.value == "frozen"
    assert decoded.relative_path == "stats/full-artifact"
    assert decoded.scientific_fingerprint == scientific
    assert decoded.payload_checksum == result.manifest.payload_checksum
    assert decoded.schema_version == CURRENT_ARTIFACT_SCHEMA_VERSION
    assert len(decoded.parents) == 1
    assert decoded.parents[0].parent_key == parent_key
    assert decoded.creation_timestamp == 42.5
    assert decoded.environment_identity == "ci-test-runner"


def test_payload_filename_uses_format_value(tmp_path: Path) -> None:
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _bytes_request(artifact_format=ArtifactFormat.PARQUET)
    )
    assert result.success
    assert (tmp_path / "reports/test-artifact/payload.parquet").exists()


def test_payload_filename_for_safetensors_format(tmp_path: Path) -> None:
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _bytes_request(b"safetensors data", artifact_format=ArtifactFormat.SAFETENSORS)
    )
    assert result.success
    assert (tmp_path / "reports/test-artifact/payload.safetensors").exists()


def test_lock_file_is_created_adjacent_to_target(tmp_path: Path) -> None:
    AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request(relative_path="deep/nested/path"))
    assert (tmp_path / "deep/nested/path").is_dir()
    assert (tmp_path / "deep/nested/path/manifest.json").exists()


def test_lock_target_path_equality_bytes_vs_file(tmp_path: Path) -> None:
    """Lock path and target path are identical for bytes and file commits with same relative_path."""
    content = b"lock test"
    source = tmp_path / "staged.dat"
    source.write_bytes(content)
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    repo.commit(_bytes_request(content, relative_path="lock/bytes"))
    repo.commit(_file_request(str(source), relative_path="lock/file"))
    assert (tmp_path / "lock/bytes/manifest.json").exists()
    assert (tmp_path / "lock/file/manifest.json").exists()


def test_repository_read_returns_payload_bytes_for_bytes_commit(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request(b"read me")).success
    result = repository.read("reports/test-artifact")
    assert result.found
    assert result.payload_bytes == b"read me"


def test_repository_read_returns_payload_bytes_for_file_commit(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"read from file")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_file_request(str(source))).success
    result = repository.read("reports/test-artifact")
    assert result.found
    assert result.payload_bytes == b"read from file"


def test_repository_read_returns_not_found_for_missing(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    result = repository.read("reports/nonexistent")
    assert not result.found


def test_repository_inspect_does_not_load_payload_bytes(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request(b"large payload" * 100)).success
    result = repository.inspect("reports/test-artifact")
    assert result.found
    assert result.manifest is not None
    assert result.payload_bytes is None  # inspect never loads payload


def test_corruption_manifest_missing(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request()).success
    (tmp_path / "reports/test-artifact/manifest.json").unlink()
    result = repository.inspect("reports/test-artifact")
    assert not result.found
    assert result.corruption_reason == ArtifactCorruptionReason.MANIFEST_MISSING


def test_corruption_payload_missing(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request()).success
    (tmp_path / "reports/test-artifact/payload.text").unlink()
    result = repository.inspect("reports/test-artifact")
    assert not result.found
    assert result.corruption_reason == ArtifactCorruptionReason.PAYLOAD_MISSING


def test_corruption_checksum_mismatch_for_bytes(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request(b"original")).success
    (tmp_path / "reports/test-artifact/payload.text").write_bytes(b"tampered")
    result = repository.inspect("reports/test-artifact")
    assert not result.found
    assert result.corruption_reason == ArtifactCorruptionReason.CHECKSUM_MISMATCH


def test_corruption_checksum_mismatch_for_file(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"original file")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_file_request(str(source))).success
    (tmp_path / "reports/test-artifact/payload.text").write_bytes(b"tampered file")
    result = repository.inspect("reports/test-artifact")
    assert not result.found
    assert result.corruption_reason == ArtifactCorruptionReason.CHECKSUM_MISMATCH


def test_corruption_schema_incompatible(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request()).success
    manifest_path = tmp_path / "reports/test-artifact/manifest.json"
    payload = json.loads(manifest_path.read_bytes())
    payload["schema_version"] = CURRENT_ARTIFACT_SCHEMA_VERSION + 99
    manifest_path.write_text(json.dumps(payload))
    result = repository.inspect("reports/test-artifact")
    assert not result.found
    assert result.corruption_reason == ArtifactCorruptionReason.SCHEMA_INCOMPATIBLE


def test_reuse_accepts_matching_frozen_artifact_bytes(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    request = _bytes_request()
    assert repository.commit(request).success
    decision = repository.assess_reuse(
        request.metadata.relative_path,
        request.metadata.artifact_key,
        request.metadata.scientific_fingerprint,
        request.metadata.execution_fingerprint,
    )
    assert decision.can_reuse
    assert decision.existing_manifest is not None


def test_reuse_accepts_matching_frozen_artifact_file(tmp_path: Path) -> None:
    source = tmp_path / "staged.dat"
    source.write_bytes(b"content")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    request = _file_request(str(source))
    assert repository.commit(request).success
    decision = repository.assess_reuse(
        request.metadata.relative_path,
        request.metadata.artifact_key,
        request.metadata.scientific_fingerprint,
        request.metadata.execution_fingerprint,
    )
    assert decision.can_reuse


def test_reuse_rejects_fingerprint_mismatch(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request()).success
    different_scientific = compute_scientific_fingerprint({"experiment": "different"})
    decision = repository.assess_reuse(
        "reports/test-artifact",
        _metadata().artifact_key,
        different_scientific,
        _metadata().execution_fingerprint,
    )
    assert not decision.can_reuse
    assert ArtifactReuseReason.SCIENTIFIC_FINGERPRINT_MISMATCH in decision.reason


def test_reuse_rejects_artifact_key_mismatch(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(_bytes_request()).success
    different_key = ArtifactKey(artifact_id=ArtifactId("different"), kind=ArtifactKind.REPORT)
    decision = repository.assess_reuse(
        "reports/test-artifact",
        different_key,
        _metadata().scientific_fingerprint,
        _metadata().execution_fingerprint,
    )
    assert not decision.can_reuse
    assert ArtifactReuseReason.KEY_MISMATCH in decision.reason


def test_reuse_rejects_missing_artifact(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    decision = repository.assess_reuse(
        "reports/nonexistent",
        _metadata().artifact_key,
        _metadata().scientific_fingerprint,
        _metadata().execution_fingerprint,
    )
    assert not decision.can_reuse
    assert decision.reason == (ArtifactReuseReason.ARTIFACT_NOT_COMMITTED,)


def test_parent_directory_is_created_by_commit(tmp_path: Path) -> None:
    AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request(relative_path="deep/nested/artifact"))
    assert (tmp_path / "deep/nested/artifact").is_dir()
    assert (tmp_path / "deep/nested/artifact/manifest.json").exists()


def test_failure_before_replace_leaves_no_visible_partial_artifact_bytes(tmp_path: Path) -> None:
    """When manifest encode fails, the exception propagates but no partial directory is visible."""
    target_dir = tmp_path / "reports/test-artifact"

    with patch(
        "datp_core.artifacts.repository.encode_manifest",
        side_effect=ValueError("simulated encode failure"),
    ):
        with pytest.raises(ValueError, match="simulated encode failure"):
            AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request())

    assert not target_dir.exists()


def test_failure_before_replace_leaves_no_visible_partial_artifact_file(tmp_path: Path) -> None:
    """When manifest encode fails for file commit, the exception propagates but no partial artifact remains."""
    source = tmp_path / "staged.dat"
    source.write_bytes(b"staged content")
    target_dir = tmp_path / "reports/test-artifact"

    with patch(
        "datp_core.artifacts.repository.encode_manifest",
        side_effect=ValueError("simulated encode failure"),
    ):
        with pytest.raises(ValueError, match="simulated encode failure"):
            AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_file_request(str(source)))

    assert not target_dir.exists()


def test_failure_during_payload_write_leaves_no_artifact(tmp_path: Path) -> None:
    """If the payload write itself fails, the temp dir is cleaned and no artifact appears."""
    target_dir = tmp_path / "reports/test-artifact"

    with patch("builtins.open", side_effect=OSError("simulated write failure")):
        with pytest.raises(OSError, match="simulated write failure"):
            AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(_bytes_request())

    assert not target_dir.exists()


def test_successful_commit_produces_exactly_manifest_and_payload(tmp_path: Path) -> None:
    """After a successful commit, the target dir contains exactly manifest.json and payload.{fmt}."""
    result = AtomicArtifactRepository(tmp_path, lock_timeout=1.0).commit(
        _bytes_request(artifact_format=ArtifactFormat.JSON)
    )
    assert result.success
    contents = set(p.name for p in (tmp_path / "reports/test-artifact").iterdir())
    assert contents == {"manifest.json", "payload.json"}


def test_fingerprints_are_identical_for_bytes_and_file_with_same_metadata(tmp_path: Path) -> None:
    content = b"same data"
    source = tmp_path / "staged.dat"
    source.write_bytes(content)
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    bytes_result = repo.commit(_bytes_request(content, relative_path="proj/bytes"))
    file_result = repo.commit(_file_request(str(source), relative_path="proj/file"))
    assert bytes_result.manifest is not None
    assert file_result.manifest is not None
    assert bytes_result.manifest.scientific_fingerprint == file_result.manifest.scientific_fingerprint
    assert bytes_result.manifest.execution_fingerprint == file_result.manifest.execution_fingerprint


def test_strict_manifest_decode_is_identical_for_bytes_and_file(tmp_path: Path) -> None:
    content = b"strict test"
    source = tmp_path / "staged.dat"
    source.write_bytes(content)
    repo = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    repo.commit(_bytes_request(content, relative_path="strict/bytes"))
    repo.commit(_file_request(str(source), relative_path="strict/file"))

    bytes_decoded = decode_manifest((tmp_path / "strict/bytes/manifest.json").read_bytes())
    file_decoded = decode_manifest((tmp_path / "strict/file/manifest.json").read_bytes())

    assert bytes_decoded.payload_checksum == file_decoded.payload_checksum
    assert bytes_decoded.scientific_fingerprint == file_decoded.scientific_fingerprint
    assert bytes_decoded.execution_fingerprint == file_decoded.execution_fingerprint
    assert bytes_decoded.schema_version == file_decoded.schema_version
