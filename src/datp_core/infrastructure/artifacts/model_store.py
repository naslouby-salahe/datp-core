"""Model tensor persistence using SafeTensors, committed through the one atomic artifact transaction."""

from __future__ import annotations

import torch
from safetensors.torch import load as load_safetensors_bytes
from safetensors.torch import save as save_safetensors_bytes

from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactCommitResult,
    ArtifactFormat,
    ArtifactKey,
    ArtifactParent,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.domain.fingerprints import Fingerprint
from datp_core.domain.identifiers import ExperimentId
from datp_core.domain.values import Seed


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
