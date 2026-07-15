from dataclasses import dataclass
from datetime import datetime

from datp_core.domain.artifacts.references import (
    ArtifactRef,
    ArtifactReferenceCollection,
    StageFingerprint,
    StageRunIdentity,
)
from datp_core.domain.learning.scores import ScoringBatchSpec
from datp_core.domain.learning.training import DeterminismLevel, PrecisionMode, TrainingBatchSpec
from datp_core.domain.runtime.admissibility import WorkerCount
from datp_core.domain.runtime.policies import DeviceSpec, HardwareInventory


@dataclass(frozen=True, slots=True, kw_only=True)
class CodeState:
    commit_identity: str | None
    is_dirty: bool | None
    dirty_diff_hash: str | None
    source_package_version: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyLockState:
    lock_identity: str | None
    scikit_learn_version: str | None
    pyarrow_version: str | None
    numpy_version: str | None
    scipy_version: str | None
    blake3_version: str | None
    msgspec_version: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class EnvironmentInventory:
    hardware: HardwareInventory
    selected_device: DeviceSpec
    precision: PrecisionMode
    determinism: DeterminismLevel
    training_batch: TrainingBatchSpec
    scoring_batch: ScoringBatchSpec
    dataloader_workers: WorkerCount
    scikit_learn_version: str | None
    pyarrow_version: str | None
    numpy_version: str | None
    scipy_version: str | None
    blake3_version: str | None
    msgspec_version: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProvenanceRecord:
    artifact: ArtifactRef
    produced_by: StageRunIdentity
    stage_fingerprint: StageFingerprint
    inputs: ArtifactReferenceCollection
    consumed_by: tuple[StageRunIdentity, ...]
    code_state: CodeState
    dependency_lock_state: DependencyLockState
    environment: EnvironmentInventory
    timestamp: datetime
