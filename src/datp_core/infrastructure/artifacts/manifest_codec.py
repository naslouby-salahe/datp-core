"""One strict, shared manifest codec: encodes/decodes ``ArtifactManifest`` as canonical JSON.

Uses ``msgspec`` structs (frozen, unknown-field-rejecting) as the wire contract so malformed
manifests, unknown enum values, and incompatible schema versions are rejected precisely and
distinctly, rather than collapsing into one generic corruption reason.
"""

from __future__ import annotations

import msgspec

from datp_core.domain.artifacts import (
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactManifest,
    ArtifactParent,
    ArtifactState,
)
from datp_core.domain.fingerprints import Checksum, Fingerprint
from datp_core.domain.identifiers import ArtifactId, ExperimentId
from datp_core.domain.values import Seed

CURRENT_ARTIFACT_SCHEMA_VERSION = 1


class ManifestDecodeError(ValueError):
    """Raised when manifest bytes are not valid, strict, well-formed manifest JSON."""


class ManifestSchemaIncompatibleError(ValueError):
    """Raised when a manifest's schema_version does not match the current codec version."""


class _ArtifactParentWire(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    artifact_id: str
    artifact_kind: str
    scientific_fingerprint: str


class _ArtifactManifestWire(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    artifact_id: str
    artifact_kind: str
    artifact_format: str
    scientific_fingerprint: str
    execution_fingerprint: str
    payload_checksum: str
    relative_path: str
    state: str
    schema_version: int
    parents: list[_ArtifactParentWire]
    creation_timestamp: float
    environment_identity: str
    experiment_id: str | None
    seed: int | None
    is_frozen: bool


def encode_manifest(manifest: ArtifactManifest) -> bytes:
    """Canonical manifest JSON payload shared by every atomic commit transaction."""
    wire = _ArtifactManifestWire(
        artifact_id=manifest.artifact_key.artifact_id.value,
        artifact_kind=manifest.artifact_key.kind.value,
        artifact_format=manifest.artifact_format.value,
        scientific_fingerprint=manifest.scientific_fingerprint.value,
        execution_fingerprint=manifest.execution_fingerprint.value,
        payload_checksum=manifest.payload_checksum.value,
        relative_path=manifest.relative_path,
        state=manifest.state.value,
        schema_version=manifest.schema_version,
        parents=[
            _ArtifactParentWire(
                artifact_id=parent.parent_key.artifact_id.value,
                artifact_kind=parent.parent_key.kind.value,
                scientific_fingerprint=parent.scientific_fingerprint.value,
            )
            for parent in manifest.parents
        ],
        creation_timestamp=manifest.creation_timestamp,
        environment_identity=manifest.environment_identity,
        experiment_id=manifest.experiment_id.value if manifest.experiment_id else None,
        seed=manifest.seed.value if manifest.seed else None,
        is_frozen=manifest.is_frozen,
    )
    return msgspec.json.encode(wire)


def decode_manifest(payload: bytes) -> ArtifactManifest:
    """Strictly decode manifest JSON bytes, rejecting unknown fields and invalid enum values.

    Raises ``ManifestSchemaIncompatibleError`` when the schema version does not match the
    current codec, and ``ManifestDecodeError`` for every other malformed-manifest condition.
    """
    try:
        wire = msgspec.json.decode(payload, type=_ArtifactManifestWire, strict=True)
    except (msgspec.DecodeError, msgspec.ValidationError) as exc:
        raise ManifestDecodeError(f"Manifest failed strict decoding: {exc}") from exc

    if wire.schema_version != CURRENT_ARTIFACT_SCHEMA_VERSION:
        raise ManifestSchemaIncompatibleError(
            f"Manifest schema_version {wire.schema_version} is incompatible with "
            f"codec version {CURRENT_ARTIFACT_SCHEMA_VERSION}"
        )

    try:
        artifact_format = ArtifactFormat(wire.artifact_format)
        artifact_kind = ArtifactKind(wire.artifact_kind)
        state = ArtifactState(wire.state)
        parents = tuple(
            ArtifactParent(
                parent_key=ArtifactKey(
                    artifact_id=ArtifactId(parent.artifact_id),
                    kind=ArtifactKind(parent.artifact_kind),
                ),
                scientific_fingerprint=Fingerprint(parent.scientific_fingerprint),
            )
            for parent in wire.parents
        )
        return ArtifactManifest(
            artifact_key=ArtifactKey(artifact_id=ArtifactId(wire.artifact_id), kind=artifact_kind),
            artifact_format=artifact_format,
            state=state,
            relative_path=wire.relative_path,
            scientific_fingerprint=Fingerprint(wire.scientific_fingerprint),
            execution_fingerprint=Fingerprint(wire.execution_fingerprint),
            payload_checksum=Checksum(wire.payload_checksum),
            schema_version=wire.schema_version,
            parents=parents,
            creation_timestamp=wire.creation_timestamp,
            environment_identity=wire.environment_identity,
            experiment_id=ExperimentId(wire.experiment_id) if wire.experiment_id is not None else None,
            seed=Seed(wire.seed) if wire.seed is not None else None,
            is_frozen=wire.is_frozen,
        )
    except ValueError as exc:
        raise ManifestDecodeError(f"Manifest contains an invalid value: {exc}") from exc
