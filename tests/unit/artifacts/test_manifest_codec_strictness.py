"""Strict manifest codec: malformed JSON, unknown fields, unknown enum values, and schema
version mismatches are each rejected precisely -- not collapsed silently or accepted."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp_core.artifacts.codec import (
    CURRENT_ARTIFACT_SCHEMA_VERSION,
    ManifestDecodeError,
    ManifestSchemaIncompatibleError,
    decode_manifest,
    encode_manifest,
)
from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactCorruptionReason,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactManifest,
    ArtifactState,
    BytesPayload,
)
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.config.fingerprints import compute_fingerprint
from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import ArtifactId


def _manifest() -> ArtifactManifest:
    scientific = compute_fingerprint("scientific", {"experiment": "codec-test"})
    return ArtifactManifest(
        artifact_key=ArtifactKey(artifact_id=ArtifactId("codec-artifact"), kind=ArtifactKind.REPORT),
        artifact_format=ArtifactFormat.TEXT,
        state=ArtifactState.FROZEN,
        relative_path="reports/codec-artifact",
        scientific_fingerprint=scientific,
        execution_fingerprint=compute_fingerprint("execution", {"scientific": scientific}),
        payload_checksum=Checksum("a" * 64),
        schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
        parents=(),
        creation_timestamp=1.0,
        environment_identity="test",
    )


def test_a_valid_manifest_round_trips_with_every_field_intact() -> None:
    manifest = _manifest()
    decoded = decode_manifest(encode_manifest(manifest))
    assert decoded == manifest


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(ManifestDecodeError):
        decode_manifest(b"{not valid json")


def test_manifest_with_an_unknown_top_level_field_is_rejected() -> None:
    payload = json.loads(encode_manifest(_manifest()))
    payload["an_unexpected_field"] = "unexpected"
    encoded = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestDecodeError):
        decode_manifest(encoded)


def test_manifest_with_an_unknown_artifact_format_enum_value_is_rejected() -> None:
    payload = json.loads(encode_manifest(_manifest()))
    payload["artifact_format"] = "not_a_real_format"
    encoded = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestDecodeError):
        decode_manifest(encoded)


def test_manifest_with_a_missing_required_field_is_rejected() -> None:
    payload = json.loads(encode_manifest(_manifest()))
    del payload["schema_version"]
    encoded = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestDecodeError):
        decode_manifest(encoded)


def test_schema_version_mismatch_is_reported_distinctly_from_malformed_manifest() -> None:
    payload = json.loads(encode_manifest(_manifest()))
    payload["schema_version"] = CURRENT_ARTIFACT_SCHEMA_VERSION + 1
    encoded = json.dumps(payload).encode("utf-8")
    with pytest.raises(ManifestSchemaIncompatibleError):
        decode_manifest(encoded)


def test_committed_artifact_with_incompatible_schema_version_reports_schema_incompatible(tmp_path: Path) -> None:
    scientific = compute_fingerprint("scientific", {"experiment": "schema-mismatch"})
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=ArtifactKey(artifact_id=ArtifactId("schema-mismatch"), kind=ArtifactKind.REPORT),
            artifact_format=ArtifactFormat.TEXT,
            scientific_fingerprint=scientific,
            execution_fingerprint=compute_fingerprint("execution", {"scientific": scientific}),
            relative_path="reports/schema-mismatch",
            parents=(),
            schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
            creation_timestamp=1.0,
            environment_identity="test",
        ),
        payload=BytesPayload(payload_bytes=b"payload"),
    )
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    assert repository.commit(request).success

    manifest_path = tmp_path / "reports/schema-mismatch/manifest.json"
    payload = json.loads(manifest_path.read_bytes())
    payload["schema_version"] = CURRENT_ARTIFACT_SCHEMA_VERSION + 1
    manifest_path.write_text(json.dumps(payload))

    result = repository.inspect("reports/schema-mismatch")
    assert not result.found
    assert result.corruption_reason == ArtifactCorruptionReason.SCHEMA_INCOMPATIBLE
