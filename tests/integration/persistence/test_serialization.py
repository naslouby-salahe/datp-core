from pathlib import Path

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType, ManifestType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion
from datp_core.infrastructure.persistence.serialization import (
    DecodedManifestRecord,
    ManifestRecord,
    deserialize_manifest_record,
    serialize_manifest_record,
)


def test_synthetic_manifest_persists_and_deserializes_with_unchanged_schema_version(tmp_path: Path) -> None:
    version = ArtifactSchemaVersion(value="v1")
    record = ManifestRecord(
        manifest_type=ManifestType.SPLIT,
        artifact=ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "c" * 64),
            artifact_type=ArtifactType.SPLIT_MANIFEST,
            content_hash="d" * 64,
            schema_version=version,
            serialization_format=SerializationFormat.JSON,
        ),
        schema_version=version,
        payload=b"synthetic split manifest",
    )
    path = tmp_path / "manifest.msgspec.json"
    path.write_bytes(serialize_manifest_record(record))

    assert deserialize_manifest_record(path.read_bytes(), expected_schema_version=version) == DecodedManifestRecord(
        record=record
    )
