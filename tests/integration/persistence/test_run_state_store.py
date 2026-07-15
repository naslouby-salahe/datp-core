from datetime import UTC, datetime
from pathlib import Path

from datp_core.domain.artifacts.keys import StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.runtime.policies import PipelineStage, RunStatus
from datp_core.infrastructure.persistence.roots import bind_storage_root
from datp_core.infrastructure.persistence.run_state import (
    FileRunStateStore,
    StageBlockRecord,
    StageCompletionRecord,
    StageFailureRecord,
    StageRecoveryRecord,
    StageReuseRecord,
    StageStartRecord,
)


def test_synthetic_lifecycle_sequence_is_durable_and_queryable(tmp_path: Path) -> None:
    store = FileRunStateStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.RUN_STATE, visibility=StorageVisibility.EPHEMERAL),
            absolute_path=tmp_path,
        )
    )
    cell_id = CellId(value="E-C1#0123456789abcdef")
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    completed = StageFingerprint(value="a" * 64)
    reused = StageFingerprint(value="b" * 64)
    blocked = StageFingerprint(value="c" * 64)
    failed = StageFingerprint(value="d" * 64)
    recovered = StageFingerprint(value="e" * 64)
    stage = PipelineStage.TRAIN
    store.append(StageStartRecord(stage=stage, cell_id=cell_id, stage_fingerprint=completed, timestamp=timestamp))
    store.append(StageCompletionRecord(stage=stage, cell_id=cell_id, stage_fingerprint=completed, timestamp=timestamp))
    store.append(StageReuseRecord(stage=stage, cell_id=cell_id, stage_fingerprint=reused, timestamp=timestamp))
    store.append(StageBlockRecord(stage=stage, cell_id=cell_id, stage_fingerprint=blocked, timestamp=timestamp))
    store.append(
        StageFailureRecord(
            stage=stage,
            cell_id=cell_id,
            stage_fingerprint=failed,
            timestamp=timestamp,
            error_family="TrainingError",
        )
    )
    store.append(StageRecoveryRecord(stage=stage, cell_id=cell_id, stage_fingerprint=recovered, timestamp=timestamp))

    reloaded = FileRunStateStore(root=store.root)
    assert reloaded.status_of(completed) is RunStatus.COMPLETED
    assert reloaded.status_of(reused) is RunStatus.REUSED
    assert reloaded.status_of(blocked) is RunStatus.BLOCKED
    assert reloaded.status_of(failed) is RunStatus.FAILED
    assert reloaded.status_of(recovered) is RunStatus.RECOVERED
