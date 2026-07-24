"""SafeTensors model weights go through the same atomic-commit transaction as every other
artifact format: lock, tmp-dir/fsync, checksum, and manifest -- not a bare unlocked file write."""

from __future__ import annotations

from pathlib import Path

import torch

from datp_core.artifacts.codecs.manifest import CURRENT_ARTIFACT_SCHEMA_VERSION
from datp_core.artifacts.codecs.safetensors import load_model_safetensors, save_model_safetensors
from datp_core.artifacts.identity import ArtifactCorruptionReason, ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.config.fingerprinting.canonical import compute_fingerprint
from datp_core.core.identifiers import ExperimentId
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey


def _checkpoint_key(label: str = "model-checkpoint") -> ArtifactKey:
    return ArtifactKey(
        node_key=StageNodeKey(experiment=ExperimentId("test"), stage=StageKind.PREFLIGHT, seed=hash(label) % 10000),
        kind=ArtifactKind.MODEL_CHECKPOINT,
    )


def _tensor_state_dict() -> dict[str, torch.Tensor]:
    return {"encoder.0.weight": torch.arange(6, dtype=torch.float32).reshape(2, 3)}


def test_safetensors_commit_round_trips_through_checksum_verification(tmp_path: Path) -> None:
    scientific = compute_fingerprint("scientific", {"experiment": "safetensors-test"})
    execution = compute_fingerprint("execution", {"scientific": scientific})
    state_dict = _tensor_state_dict()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)

    result = save_model_safetensors(
        state_dict,
        repository=repository,
        artifact_key=_checkpoint_key(),
        scientific_fingerprint=scientific,
        execution_fingerprint=execution,
        relative_path="experiments/test/preflight/model-checkpoint",
        schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
        creation_timestamp=1.0,
        environment_identity="test",
    )
    assert result.success
    assert result.manifest is not None
    assert result.manifest.artifact_format == ArtifactFormat.SAFETENSORS

    loaded = load_model_safetensors("experiments/test/preflight/model-checkpoint", repository)
    assert torch.equal(loaded["encoder.0.weight"], state_dict["encoder.0.weight"])


def test_corrupted_safetensors_payload_is_rejected_identically_to_other_formats(tmp_path: Path) -> None:
    scientific = compute_fingerprint("scientific", {"experiment": "safetensors-corruption"})
    execution = compute_fingerprint("execution", {"scientific": scientific})
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)

    result = save_model_safetensors(
        _tensor_state_dict(),
        repository=repository,
        artifact_key=_checkpoint_key("corrupt-checkpoint"),
        scientific_fingerprint=scientific,
        execution_fingerprint=execution,
        relative_path="experiments/test/preflight/corrupt-checkpoint",
        schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
        creation_timestamp=1.0,
        environment_identity="test",
    )
    assert result.success

    payload_path = tmp_path / "experiments/test/preflight/corrupt-checkpoint/payload.safetensors"
    payload_path.write_bytes(b"corrupted safetensors payload")

    inspection = repository.inspect("experiments/test/preflight/corrupt-checkpoint")
    assert not inspection.found
    assert inspection.corruption_reason == ArtifactCorruptionReason.CHECKSUM_MISMATCH
