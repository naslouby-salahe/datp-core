from dataclasses import dataclass
from os import O_DIRECTORY, O_RDONLY, close, fsync, replace
from os import open as open_file
from pathlib import Path
from tempfile import NamedTemporaryFile

import msgspec

from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.artifacts.lineage import RecoveryCompatibilityIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.errors import ResumeIncompatibilityError
from datp_core.domain.learning.checkpoints import RecoveryState
from datp_core.infrastructure.persistence.roots import BoundStorageRoot

CHECKPOINT_STORE_NAMESPACE = ".checkpoint-store"


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryStateRepository:
    root: BoundStorageRoot

    def __post_init__(self) -> None:
        if self.root.spec.kind is not StorageRootKind.RECOVERY_STATE:
            raise ValueError("recovery state repository requires the recovery-state root")

    def load(self, compatibility_identity: RecoveryCompatibilityIdentity) -> RecoveryState | None:
        path = self._path(compatibility_identity)
        if not path.exists():
            return None
        return self._read(path=path, expected_identity=compatibility_identity)

    def save(self, recovery_state: RecoveryState) -> None:
        _validate_recovery_state(recovery_state)
        path = self._path(recovery_state.compatibility_identity)
        existing_state = (
            self._read(path=path, expected_identity=recovery_state.compatibility_identity) if path.exists() else None
        )
        if existing_state is not None and existing_state != recovery_state:
            raise _mismatch_error(
                detail="recovery compatibility identity already refers to distinct immutable state",
                state=recovery_state,
            )
        _write_recovery_state(path=path, recovery_state=recovery_state)

    def _path(self, compatibility_identity: RecoveryCompatibilityIdentity) -> Path:
        filename = f"{compatibility_identity.value.value}.json"
        return self.root.absolute_path / CHECKPOINT_STORE_NAMESPACE / "recovery" / filename

    def _read(self, *, path: Path, expected_identity: RecoveryCompatibilityIdentity) -> RecoveryState:
        try:
            recovery_state = msgspec.json.decode(path.read_bytes(), type=RecoveryState)
        except (OSError, msgspec.DecodeError, msgspec.ValidationError) as error:
            raise ResumeIncompatibilityError(
                detail="recovery metadata is unreadable or incompatible",
                training_identity=expected_identity.value.value,
                round_number=0,
            ) from error
        _validate_recovery_state(recovery_state)
        if recovery_state.compatibility_identity != expected_identity:
            raise _mismatch_error(
                detail="recovery metadata compatibility identity does not match its storage namespace",
                state=recovery_state,
            )
        return recovery_state


def _validate_recovery_state(recovery_state: RecoveryState) -> None:
    references = (
        recovery_state.model_state_ref,
        recovery_state.optimizer_state_ref,
        recovery_state.scheduler_state_ref,
        recovery_state.federation_state_ref,
        recovery_state.rng_state_ref,
    )
    if any(reference.artifact_type is not ArtifactType.RECOVERY_CHECKPOINT for reference in references):
        raise _mismatch_error(
            detail="recovery state may reference only recovery-checkpoint artifacts",
            state=recovery_state,
        )
    if recovery_state.last_completed_round.value < 1:
        raise _mismatch_error(
            detail="recovery state must record a completed positive round",
            state=recovery_state,
        )


def _write_recovery_state(*, path: Path, recovery_state: RecoveryState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=".recovery-", delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(msgspec.json.encode(recovery_state))
            temporary_file.flush()
            fsync(temporary_file.fileno())
        replace(temporary_path, path)
        _fsync_directory(path.parent)
    except OSError as error:
        raise _mismatch_error(
            detail="recovery metadata atomic commit did not complete",
            state=recovery_state,
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = open_file(path, O_RDONLY | O_DIRECTORY)
    try:
        fsync(descriptor)
    finally:
        close(descriptor)


def _mismatch_error(*, detail: str, state: RecoveryState) -> ResumeIncompatibilityError:
    return ResumeIncompatibilityError(
        detail=detail,
        training_identity=state.compatibility_identity.value.value,
        round_number=state.last_completed_round.value,
    )
