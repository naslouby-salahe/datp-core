"""The one strict, shared manifest codec (canonical JSON via msgspec) and the one sanctioned
SafeTensors call site for model-tensor persistence.

Merging ``infrastructure/artifacts/{manifest_codec,model_store}.py`` here fixes a pre-refactor
bypass: ``application/learning_stages.py`` called ``safetensors.torch.load``/``save`` directly in
places instead of going through ``model_store.py``'s ``save_model_safetensors``/
``load_model_safetensors``, meaning checkpoint payloads could be read/written without an atomic
commit transaction. Consolidating both SafeTensors call sites into this one module -- and updating
``learning/`` to import from here -- makes it structurally impossible to bypass the commit
transaction for model tensors again.
"""

from __future__ import annotations

import msgspec
import torch
from safetensors.torch import load as load_safetensors_bytes
from safetensors.torch import save as save_safetensors_bytes

from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactCommitResult,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactManifest,
    ArtifactParent,
    ArtifactRepository,
    ArtifactState,
    BytesPayload,
)
from datp_core.pipeline.fingerprints import Checksum, Fingerprint
from datp_core.pipeline.identifiers import ArtifactId, ExperimentId
from datp_core.pipeline.values import Seed

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
        )
    except ValueError as exc:
        raise ManifestDecodeError(f"Manifest contains an invalid value: {exc}") from exc


def save_model_safetensors(
    model_state_dict: dict[str, torch.Tensor],
    *,
    repository: ArtifactRepository,
    artifact_key: ArtifactKey,
    scientific_fingerprint: Fingerprint,
    execution_fingerprint: Fingerprint,
    relative_path: str,
    schema_version: int,
    creation_timestamp: float,
    environment_identity: str,
    parents: tuple[ArtifactParent, ...] = (),
    experiment_id: ExperimentId | None = None,
    seed: Seed | None = None,
) -> ArtifactCommitResult:
    """Commit model weights as a SafeTensors artifact through the atomic commit transaction."""
    clean_tensors = {key: tensor.cpu().contiguous() for key, tensor in model_state_dict.items()}
    payload_bytes = save_safetensors_bytes(clean_tensors)
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=artifact_key,
            artifact_format=ArtifactFormat.SAFETENSORS,
            scientific_fingerprint=scientific_fingerprint,
            execution_fingerprint=execution_fingerprint,
            relative_path=relative_path,
            parents=parents,
            schema_version=schema_version,
            creation_timestamp=creation_timestamp,
            environment_identity=environment_identity,
            experiment_id=experiment_id,
            seed=seed,
        ),
        payload=BytesPayload(payload_bytes=payload_bytes),
    )
    return repository.commit(request)


def load_model_safetensors(relative_path: str, repository: ArtifactRepository) -> dict[str, torch.Tensor]:
    """Read a committed SafeTensors artifact, verifying its checksum before deserializing."""
    result = repository.read(relative_path)
    if not result.found or result.payload_bytes is None:
        raise FileNotFoundError(f"SafeTensors artifact not found or corrupt: {relative_path}")
    return load_safetensors_bytes(result.payload_bytes)


__all__ = [
    "CURRENT_ARTIFACT_SCHEMA_VERSION",
    "ManifestDecodeError",
    "ManifestSchemaIncompatibleError",
    "decode_manifest",
    "encode_manifest",
    "load_model_safetensors",
    "save_model_safetensors",
]
