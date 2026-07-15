from dataclasses import dataclass

import msgspec

from datp_core.domain.artifacts.lineage import SchemaCompatibility
from datp_core.domain.artifacts.manifests import ManifestType
from datp_core.domain.artifacts.provenance import ProvenanceRecord
from datp_core.domain.artifacts.references import ArtifactRef, ArtifactSchemaVersion


@dataclass(frozen=True, slots=True, kw_only=True)
class ManifestRecord:
    manifest_type: ManifestType
    artifact: ArtifactRef
    schema_version: ArtifactSchemaVersion
    payload: bytes

    def __post_init__(self) -> None:
        if self.artifact.schema_version != self.schema_version:
            raise ValueError("manifest record schema version must match its artifact reference")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProvenanceRecordEnvelope:
    schema_version: ArtifactSchemaVersion
    record: ProvenanceRecord

    def __post_init__(self) -> None:
        if self.record.artifact.schema_version != self.schema_version:
            raise ValueError("provenance record schema version must match its artifact reference")


@dataclass(frozen=True, slots=True, kw_only=True)
class DecodedManifestRecord:
    record: ManifestRecord
    schema_compatibility: SchemaCompatibility = SchemaCompatibility.COMPATIBLE


@dataclass(frozen=True, slots=True, kw_only=True)
class DecodedProvenanceRecord:
    record: ProvenanceRecordEnvelope
    schema_compatibility: SchemaCompatibility = SchemaCompatibility.COMPATIBLE


@dataclass(frozen=True, slots=True, kw_only=True)
class IncompatibleSchemaVersion:
    expected: ArtifactSchemaVersion
    actual: ArtifactSchemaVersion
    schema_compatibility: SchemaCompatibility = SchemaCompatibility.INCOMPATIBLE


def serialize_manifest_record(record: ManifestRecord) -> bytes:
    return msgspec.json.encode(record)


def deserialize_manifest_record(
    serialized: bytes, *, expected_schema_version: ArtifactSchemaVersion
) -> DecodedManifestRecord | IncompatibleSchemaVersion:
    record = msgspec.json.decode(serialized, type=ManifestRecord)
    if record.schema_version != expected_schema_version:
        return IncompatibleSchemaVersion(expected=expected_schema_version, actual=record.schema_version)
    return DecodedManifestRecord(record=record)


def serialize_provenance_record(record: ProvenanceRecordEnvelope) -> bytes:
    return msgspec.json.encode(record)


def deserialize_provenance_record(
    serialized: bytes, *, expected_schema_version: ArtifactSchemaVersion
) -> DecodedProvenanceRecord | IncompatibleSchemaVersion:
    record = msgspec.json.decode(serialized, type=ProvenanceRecordEnvelope)
    if record.schema_version != expected_schema_version:
        return IncompatibleSchemaVersion(expected=expected_schema_version, actual=record.schema_version)
    return DecodedProvenanceRecord(record=record)
