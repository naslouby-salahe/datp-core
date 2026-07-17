from pathlib import Path

from datp_core.application.ports.persistence import (
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
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, CheckpointProtocol, RecoveryState
from datp_core.domain.runtime.seeds import RoundNumber, Seed
from datp_core.infrastructure.persistence.checkpoints import FileCheckpointStore
from datp_core.infrastructure.persistence.roots import bind_storage_root


def _artifact(identifier: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{identifier * 64}"),
        artifact_type=artifact_type,
        content_hash=identifier * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.TORCH_STATE,
    )


def test_synthetic_checkpoint_and_recovery_use_separate_roots_and_profiles(tmp_path: Path) -> None:
    store = FileCheckpointStore(
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
    checkpoint_artifact = _artifact("a", ArtifactType.SCIENTIFIC_CHECKPOINT)
    checkpoint = CheckpointDescriptor(
        checkpoint_id=CheckpointId(value="checkpoint-" + "b" * 64),
        round=RoundNumber(value=25),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=StageFingerprint(value="c" * 64)),
        protocol=CheckpointProtocol.COMPLETE_SCHEDULED,
        artifact_ref=checkpoint_artifact,
        content_hash=checkpoint_artifact.content_hash,
        schema_version=checkpoint_artifact.schema_version,
    )
    recovery_identity = RecoveryCompatibilityIdentity(value=StageFingerprint(value="d" * 64))
    recovery = RecoveryState(
        model_state_ref=_artifact("e", ArtifactType.RECOVERY_CHECKPOINT),
        optimizer_state_ref=_artifact("f", ArtifactType.RECOVERY_CHECKPOINT),
        scheduler_state_ref=_artifact("1", ArtifactType.RECOVERY_CHECKPOINT),
        federation_state_ref=_artifact("2", ArtifactType.RECOVERY_CHECKPOINT),
        rng_state_ref=_artifact("3", ArtifactType.RECOVERY_CHECKPOINT),
        last_completed_round=RoundNumber(value=24),
        compatibility_identity=recovery_identity,
    )

    store.save(SaveScientificCheckpointRequest(checkpoint=checkpoint, staged_artifact=checkpoint_artifact))
    store.save_recovery(SaveRecoveryStateRequest(recovery_state=recovery))

    assert (tmp_path / "scientific" / ".checkpoint-store" / "scientific").is_dir()
    assert (tmp_path / "recovery" / ".checkpoint-store" / "recovery").is_dir()
    assert (
        store.find_compatible(
            FindCheckpointRequest(
                checkpoint_id=checkpoint.checkpoint_id, training_identity=checkpoint.training_identity
            )
        ).checkpoint
        == checkpoint
    )
    assert (
        store.load_recovery(LoadRecoveryStateRequest(compatibility_identity=recovery_identity)).recovery_state
        == recovery
    )
    changed_profile_identity = RecoveryCompatibilityIdentity(value=StageFingerprint(value="4" * 64))
    assert (
        store.load_recovery(LoadRecoveryStateRequest(compatibility_identity=changed_profile_identity)).recovery_state
        is None
    )


def test_anchor_termination_checkpoint_persists_at_an_unscheduled_terminal_round(tmp_path: Path) -> None:
    store = FileCheckpointStore(
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
    checkpoint_artifact = _artifact("5", ArtifactType.SCIENTIFIC_CHECKPOINT)
    checkpoint = CheckpointDescriptor(
        checkpoint_id=CheckpointId(value="checkpoint-" + "6" * 64),
        round=RoundNumber(value=118),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=StageFingerprint(value="7" * 64)),
        protocol=CheckpointProtocol.ANCHOR_TERMINATION,
        artifact_ref=checkpoint_artifact,
        content_hash=checkpoint_artifact.content_hash,
        schema_version=checkpoint_artifact.schema_version,
    )

    store.save(SaveScientificCheckpointRequest(checkpoint=checkpoint, staged_artifact=checkpoint_artifact))

    found = store.find_compatible(
        FindCheckpointRequest(checkpoint_id=checkpoint.checkpoint_id, training_identity=checkpoint.training_identity)
    ).checkpoint
    assert found == checkpoint
    assert found is not None
    assert found.round.value == 118
    assert found.protocol is CheckpointProtocol.ANCHOR_TERMINATION
