from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType, ManifestType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion
from datp_core.infrastructure.persistence.serialization import (
    DecodedManifestRecord,
    IncompatibleSchemaVersion,
    ManifestRecord,
    deserialize_manifest_record,
    serialize_manifest_record,
)


@given(st.binary(max_size=4096))
def test_manifest_serialization_is_byte_idempotent_for_arbitrary_payloads(payload: bytes) -> None:
    version = ArtifactSchemaVersion(value="v1")
    record = ManifestRecord(
        manifest_type=ManifestType.SPLIT,
        artifact=ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "a" * 64),
            artifact_type=ArtifactType.SPLIT_MANIFEST,
            content_hash="b" * 64,
            schema_version=version,
            serialization_format=SerializationFormat.JSON,
        ),
        schema_version=version,
        payload=payload,
    )
    encoded = serialize_manifest_record(record)
    decoded = deserialize_manifest_record(encoded, expected_schema_version=version)

    assert not isinstance(decoded, IncompatibleSchemaVersion)
    assert decoded == DecodedManifestRecord(record=record)
    assert serialize_manifest_record(decoded.record) == encoded
