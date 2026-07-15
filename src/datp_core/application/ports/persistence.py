from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self

from datp_core.domain.artifacts.bundles import ArtifactBundleManifest, DeclaredTestScoreMember
from datp_core.domain.artifacts.keys import ArtifactKey, WriteDisposition
from datp_core.domain.artifacts.lineage import (
    IntegrityStatus,
    RecoveryCompatibilityIdentity,
    SchemaCompatibility,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ManifestType
from datp_core.domain.artifacts.provenance import ProvenanceRecord
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    CheckpointId,
    LockScope,
    StageFingerprint,
    ValidationStatus,
)
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, RecoveryState
from datp_core.domain.learning.scores import ClientTestScoreArtifact
from datp_core.domain.runtime.policies import RunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactLookupRequest:
    artifact_id: ArtifactId
    key: ArtifactKey


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactLookupResult:
    artifact: ArtifactRef | None


@dataclass(frozen=True, slots=True, kw_only=True)
class WriteArtifactRequest:
    key: ArtifactKey
    artifact: ArtifactRef
    content: bytes
    write_disposition: WriteDisposition


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactWriteResult:
    artifact: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactBundleMemberWrite:
    key: ArtifactKey
    declared_member: DeclaredTestScoreMember
    content: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitArtifactBundleRequest:
    aggregate: ClientTestScoreArtifact
    members: tuple[ArtifactBundleMemberWrite, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactBundleCommitResult:
    manifest: ArtifactBundleManifest
    commit_marker: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidateArtifactRequest:
    key: ArtifactKey
    artifact: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactValidationResult:
    artifact: ArtifactRef
    status: ValidationStatus
    integrity: IntegrityStatus
    schema_compatibility: SchemaCompatibility


@dataclass(frozen=True, slots=True, kw_only=True)
class FindCheckpointRequest:
    checkpoint_id: CheckpointId
    training_identity: TrainingIdentity


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointLookupResult:
    checkpoint: CheckpointDescriptor | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SaveScientificCheckpointRequest:
    checkpoint: CheckpointDescriptor
    staged_artifact: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointWriteResult:
    checkpoint: CheckpointDescriptor


@dataclass(frozen=True, slots=True, kw_only=True)
class SaveRecoveryStateRequest:
    recovery_state: RecoveryState


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryWriteResult:
    recovery_state: RecoveryState


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadRecoveryStateRequest:
    compatibility_identity: RecoveryCompatibilityIdentity


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryLookupResult:
    recovery_state: RecoveryState | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AcquireArtifactLockRequest:
    artifact_id: ArtifactId
    owner: str
    scope: LockScope
    timeout_seconds: int
    heartbeat_seconds: int | None


class ArtifactLockLease(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def release(self) -> None: ...

    def renew(self) -> None: ...


class ArtifactStore(Protocol):
    def lookup(self, request: ArtifactLookupRequest) -> ArtifactLookupResult: ...

    def write_atomically(self, request: WriteArtifactRequest) -> ArtifactWriteResult: ...

    def commit_bundle(self, request: CommitArtifactBundleRequest) -> ArtifactBundleCommitResult: ...

    def validate_integrity(self, request: ValidateArtifactRequest) -> ArtifactValidationResult: ...


class CheckpointStore(Protocol):
    def find_compatible(self, request: FindCheckpointRequest) -> CheckpointLookupResult: ...

    def save(self, request: SaveScientificCheckpointRequest) -> CheckpointWriteResult: ...

    def save_recovery(self, request: SaveRecoveryStateRequest) -> RecoveryWriteResult: ...

    def load_recovery(self, request: LoadRecoveryStateRequest) -> RecoveryLookupResult: ...


class ManifestStore(Protocol):
    def record(self, manifest: ManifestType) -> None: ...

    def trace(self, output_id: str) -> tuple[ProvenanceRecord, ...]: ...


class RunStateStore(Protocol):
    def append(self, record: object) -> None: ...

    def status_of(self, stage_fingerprint: StageFingerprint) -> RunStatus: ...


class ArtifactLockProvider(Protocol):
    def acquire(self, request: AcquireArtifactLockRequest) -> ArtifactLockLease: ...
