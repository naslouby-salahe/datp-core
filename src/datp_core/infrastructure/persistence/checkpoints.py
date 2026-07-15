from dataclasses import dataclass
from os import O_DIRECTORY, O_RDONLY, close, fsync, replace
from os import open as open_file
from pathlib import Path
from tempfile import NamedTemporaryFile

import msgspec

from datp_core.application.ports.persistence import (
    CheckpointLookupResult,
    CheckpointWriteResult,
    FindCheckpointRequest,
    LoadRecoveryStateRequest,
    RecoveryLookupResult,
    RecoveryWriteResult,
    SaveRecoveryStateRequest,
    SaveScientificCheckpointRequest,
)
from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.errors import CheckpointError
from datp_core.domain.learning.checkpoints import CheckpointDescriptor
from datp_core.infrastructure.persistence.recovery import RecoveryStateRepository
from datp_core.infrastructure.persistence.roots import BoundStorageRoot


@dataclass(frozen=True, slots=True, kw_only=True)
class FileCheckpointStore:
    scientific_root: BoundStorageRoot
    recovery_root: BoundStorageRoot

    def __post_init__(self) -> None:
        if self.scientific_root.spec.kind is not StorageRootKind.SCIENTIFIC_CHECKPOINTS:
            raise ValueError("scientific checkpoint store requires the scientific-checkpoints root")
        if self.recovery_root.spec.kind is not StorageRootKind.RECOVERY_STATE:
            raise ValueError("recovery checkpoint store requires the recovery-state root")

    def find_compatible(self, request: FindCheckpointRequest) -> CheckpointLookupResult:
        path = _scientific_path(root=self.scientific_root, checkpoint_id=request.checkpoint_id.value)
        if not path.exists():
            return CheckpointLookupResult(checkpoint=None)
        checkpoint = _read_scientific(path=path, checkpoint_id=request.checkpoint_id.value)
        if checkpoint.training_identity != request.training_identity:
            return CheckpointLookupResult(checkpoint=None)
        return CheckpointLookupResult(checkpoint=checkpoint)

    def save(self, request: SaveScientificCheckpointRequest) -> CheckpointWriteResult:
        if request.staged_artifact != request.checkpoint.artifact_ref:
            raise CheckpointError(
                detail="scientific checkpoint staged artifact does not match its descriptor",
                checkpoint_id=request.checkpoint.checkpoint_id.value,
                content_hash=request.checkpoint.content_hash,
            )
        path = _scientific_path(root=self.scientific_root, checkpoint_id=request.checkpoint.checkpoint_id.value)
        if (
            path.exists()
            and _read_scientific(path=path, checkpoint_id=request.checkpoint.checkpoint_id.value) != request.checkpoint
        ):
            raise CheckpointError(
                detail="scientific checkpoint id is immutable and already refers to distinct content",
                checkpoint_id=request.checkpoint.checkpoint_id.value,
                content_hash=request.checkpoint.content_hash,
            )
        _write_record(path=path, record=request.checkpoint)
        return CheckpointWriteResult(checkpoint=request.checkpoint)

    def save_recovery(self, request: SaveRecoveryStateRequest) -> RecoveryWriteResult:
        RecoveryStateRepository(root=self.recovery_root).save(request.recovery_state)
        return RecoveryWriteResult(recovery_state=request.recovery_state)

    def load_recovery(self, request: LoadRecoveryStateRequest) -> RecoveryLookupResult:
        recovery_state = RecoveryStateRepository(root=self.recovery_root).load(request.compatibility_identity)
        return RecoveryLookupResult(recovery_state=recovery_state)


def _scientific_path(*, root: BoundStorageRoot, checkpoint_id: str) -> Path:
    return root.absolute_path / ".checkpoint-store" / "scientific" / f"{checkpoint_id}.json"


def _write_record(*, path: Path, record: CheckpointDescriptor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".checkpoint-", delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(msgspec.json.encode(record))
            temporary_file.flush()
            fsync(temporary_file.fileno())
        replace(temporary_path, path)
        _fsync_directory(path.parent)
    except OSError as error:
        raise CheckpointError(
            detail="scientific checkpoint metadata atomic commit did not complete",
            checkpoint_id=record.checkpoint_id.value,
            content_hash=record.content_hash,
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _read_scientific(*, path: Path, checkpoint_id: str) -> CheckpointDescriptor:
    try:
        checkpoint = msgspec.json.decode(path.read_bytes(), type=CheckpointDescriptor)
    except (OSError, msgspec.DecodeError, msgspec.ValidationError) as error:
        raise CheckpointError(
            detail="scientific checkpoint metadata is unreadable or incompatible",
            checkpoint_id=checkpoint_id,
            content_hash="unknown",
        ) from error
    if checkpoint.checkpoint_id.value != checkpoint_id:
        raise CheckpointError(
            detail="scientific checkpoint metadata does not match its storage namespace",
            checkpoint_id=checkpoint_id,
            content_hash=checkpoint.content_hash,
        )
    return checkpoint


def _fsync_directory(path: Path) -> None:
    descriptor = open_file(path, O_RDONLY | O_DIRECTORY)
    try:
        fsync(descriptor)
    finally:
        close(descriptor)
