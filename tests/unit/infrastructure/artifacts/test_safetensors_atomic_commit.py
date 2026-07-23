"""SafeTensors model weights go through the same atomic-commit transaction as every other
artifact format: lock, tmp-dir/fsync, checksum, and manifest -- not a bare unlocked file write."""

from __future__ import annotations

from pathlib import Path

import torch

from datp_core.artifacts.models import ArtifactCorruptionReason, ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.configuration.fingerprints import compute_execution_fingerprint, compute_scientific_fingerprint
from datp_core.pipeline.identifiers import ArtifactId
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.artifacts.serialization import load_model_safetensors, save_model_safetensors


def _tensor_state_dict() -> dict[str, torch.Tensor]:
    return {"encoder.0.weight": torch.arange(6, dtype=torch.float32).reshape(2, 3)}


def test_safetensors_commit_round_trips_through_checksum_verification(tmp_path: Path) -> None:
    scientific = compute_scientific_fingerprint({"experiment": "safetensors-test"})
    execution = compute_execution_fingerprint({"scientific": scientific})
    state_dict = _tensor_state_dict()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)

    result = save_model_safetensors(
        state_dict,
        repository=repository,
        artifact_key=ArtifactKey(artifact_id=ArtifactId("model-checkpoint"), kind=ArtifactKind.MODEL_CHECKPOINT),
        scientific_fingerprint=scientific,
        execution_fingerprint=execution,
        relative_path="checkpoints/model-checkpoint",
        schema_version=1,
        creation_timestamp=1.0,
        environment_identity="test",
    )
    assert result.success
    assert result.manifest is not None
    assert result.manifest.artifact_format == ArtifactFormat.SAFETENSORS

    loaded = load_model_safetensors("checkpoints/model-checkpoint", repository)
    assert torch.equal(loaded["encoder.0.weight"], state_dict["encoder.0.weight"])


def test_corrupted_safetensors_payload_is_rejected_identically_to_other_formats(tmp_path: Path) -> None:
    scientific = compute_scientific_fingerprint({"experiment": "safetensors-corruption"})
    execution = compute_execution_fingerprint({"scientific": scientific})
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)

    result = save_model_safetensors(
        _tensor_state_dict(),
        repository=repository,
        artifact_key=ArtifactKey(artifact_id=ArtifactId("corrupt-checkpoint"), kind=ArtifactKind.MODEL_CHECKPOINT),
        scientific_fingerprint=scientific,
        execution_fingerprint=execution,
        relative_path="checkpoints/corrupt-checkpoint",
        schema_version=1,
        creation_timestamp=1.0,
        environment_identity="test",
    )
    assert result.success

    payload_path = tmp_path / "checkpoints/corrupt-checkpoint/payload.safetensors"
    payload_path.write_bytes(b"corrupted safetensors payload")

    inspection = repository.inspect("checkpoints/corrupt-checkpoint")
    assert not inspection.found
    assert inspection.corruption_reason == ArtifactCorruptionReason.CHECKSUM_MISMATCH
