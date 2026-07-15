from inspect import signature
from pathlib import Path

import pytest

from datp_core.application.ports.persistence import (
    CheckpointStore,
    FindCheckpointRequest,
    LoadRecoveryStateRequest,
    SaveRecoveryStateRequest,
    SaveScientificCheckpointRequest,
)
from datp_core.domain.artifacts.keys import (
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
)
from datp_core.domain.artifacts.lineage import RecoveryCompatibilityIdentity, TrainingIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.errors import CheckpointError, ResumeIncompatibilityError
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, RecoveryState
from datp_core.domain.runtime.seeds import RoundNumber, Seed
from datp_core.infrastructure.persistence.checkpoints import FileCheckpointStore
from datp_core.infrastructure.persistence.roots import bind_storage_root


def _store(tmp_path: Path) -> FileCheckpointStore:
    return FileCheckpointStore(
        scientific_root=bind_storage_root(
            spec=StorageRootSpec(
                kind=StorageRootKind.SCIENTIFIC_CHECKPOINTS,
                visibility=StorageVisibility.SCIENTIFIC_OUTPUT,
            ),
            absolute_path=tmp_path / "scientific",
        ),
        recovery_root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.RECOVERY_STATE, visibility=StorageVisibility.EPHEMERAL),
            absolute_path=tmp_path / "recovery",
        ),
    )


def _reference(identifier: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{identifier * 64}"),
        artifact_type=artifact_type,
        content_hash=identifier * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.TORCH_STATE,
    )


def _checkpoint() -> CheckpointDescriptor:
    reference = _reference("a", ArtifactType.SCIENTIFIC_CHECKPOINT)
    return CheckpointDescriptor(
        checkpoint_id=CheckpointId(value="checkpoint-" + "a" * 64),
        round=RoundNumber(value=25),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=StageFingerprint(value="b" * 64)),
        artifact_ref=reference,
        content_hash=reference.content_hash,
        schema_version=reference.schema_version,
    )


def _recovery() -> RecoveryState:
    identity = RecoveryCompatibilityIdentity(value=StageFingerprint(value="c" * 64))
    return RecoveryState(
        model_state_ref=_reference("d", ArtifactType.RECOVERY_CHECKPOINT),
        optimizer_state_ref=_reference("e", ArtifactType.RECOVERY_CHECKPOINT),
        scheduler_state_ref=_reference("f", ArtifactType.RECOVERY_CHECKPOINT),
        federation_state_ref=_reference("1", ArtifactType.RECOVERY_CHECKPOINT),
        rng_state_ref=_reference("2", ArtifactType.RECOVERY_CHECKPOINT),
        last_completed_round=RoundNumber(value=24),
        compatibility_identity=identity,
    )


def test_store_matches_all_four_checkpoint_port_methods(tmp_path: Path) -> None:
    _store(tmp_path)
    for method in ("find_compatible", "save", "save_recovery", "load_recovery"):
        assert signature(getattr(FileCheckpointStore, method)) == signature(getattr(CheckpointStore, method))


def test_scientific_and_recovery_records_are_distinct_and_durable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    checkpoint = _checkpoint()
    recovery = _recovery()
    store.save(SaveScientificCheckpointRequest(checkpoint=checkpoint, staged_artifact=checkpoint.artifact_ref))
    store.save_recovery(SaveRecoveryStateRequest(recovery_state=recovery))

    reloaded = _store(tmp_path)
    scientific = reloaded.find_compatible(
        FindCheckpointRequest(checkpoint_id=checkpoint.checkpoint_id, training_identity=checkpoint.training_identity)
    )
    loaded_recovery = reloaded.load_recovery(
        LoadRecoveryStateRequest(compatibility_identity=recovery.compatibility_identity)
    )
    other_scientific = reloaded.find_compatible(
        FindCheckpointRequest(
            checkpoint_id=CheckpointId(value="checkpoint-" + "c" * 64),
            training_identity=checkpoint.training_identity,
        )
    )
    assert scientific.checkpoint == checkpoint
    assert loaded_recovery.recovery_state == recovery
    assert other_scientific.checkpoint is None


def test_recovery_metadata_in_a_mismatched_namespace_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    recovery = _recovery()
    store.save_recovery(SaveRecoveryStateRequest(recovery_state=recovery))
    mismatched_identity = RecoveryCompatibilityIdentity(value=StageFingerprint(value="f" * 64))
    repository = tmp_path / "recovery" / ".checkpoint-store" / "recovery"
    original = repository / f"{recovery.compatibility_identity.value.value}.json"
    mismatched = repository / f"{mismatched_identity.value.value}.json"
    original.replace(mismatched)
    request = LoadRecoveryStateRequest(compatibility_identity=mismatched_identity)

    with pytest.raises(ResumeIncompatibilityError):
        store.load_recovery(request)


def test_recovery_content_cannot_be_decoded_as_a_scientific_checkpoint(tmp_path: Path) -> None:
    store = _store(tmp_path)
    recovery = _recovery()
    store.save_recovery(SaveRecoveryStateRequest(recovery_state=recovery))
    recovery_path = (
        tmp_path / "recovery" / ".checkpoint-store" / "recovery" / f"{recovery.compatibility_identity.value.value}.json"
    )
    scientific_checkpoint = _checkpoint()
    scientific_path = (
        tmp_path
        / "scientific"
        / ".checkpoint-store"
        / "scientific"
        / f"{scientific_checkpoint.checkpoint_id.value}.json"
    )
    scientific_path.parent.mkdir(parents=True)
    scientific_path.write_bytes(recovery_path.read_bytes())
    request = FindCheckpointRequest(
        checkpoint_id=scientific_checkpoint.checkpoint_id,
        training_identity=scientific_checkpoint.training_identity,
    )

    with pytest.raises(CheckpointError):
        store.find_compatible(request)
