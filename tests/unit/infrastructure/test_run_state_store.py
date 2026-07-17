from datetime import UTC, datetime
from inspect import signature
from pathlib import Path

import msgspec

from datp_core.application.ports.persistence import RunStateStore
from datp_core.domain.artifacts.keys import StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.runtime.policies import PipelineStage, RunStatus
from datp_core.infrastructure.persistence.roots import bind_storage_root
from datp_core.infrastructure.persistence.run_state import (
    FileRunStateStore,
    LifecycleLogEntry,
    StageBlockRecord,
    StageCompletionRecord,
    StageFailureRecord,
    StageRecoveryRecord,
    StageReuseRecord,
    StageStartRecord,
)

type LifecycleTestRecord = (
    StageStartRecord
    | StageCompletionRecord
    | StageReuseRecord
    | StageBlockRecord
    | StageFailureRecord
    | StageRecoveryRecord
)


def _store(tmp_path: Path) -> FileRunStateStore:
    return FileRunStateStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.RUN_STATE, visibility=StorageVisibility.EPHEMERAL),
            absolute_path=tmp_path,
        )
    )


def _fields() -> tuple[PipelineStage, CellId, StageFingerprint, datetime]:
    return (
        PipelineStage.TRAIN,
        CellId(value="E-C1#0123456789abcdef"),
        StageFingerprint(value="a" * 64),
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def _records() -> tuple[LifecycleTestRecord, ...]:
    stage, cell_id, fingerprint, timestamp = _fields()
    return (
        StageStartRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp),
        StageCompletionRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp),
        StageReuseRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp),
        StageBlockRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp),
        StageFailureRecord(
            stage=stage,
            cell_id=cell_id,
            stage_fingerprint=fingerprint,
            timestamp=timestamp,
            error_family="CudaOutOfMemoryError",
        ),
        StageRecoveryRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp),
    )


def test_store_matches_the_narrow_run_state_port_signature(tmp_path: Path) -> None:
    _store(tmp_path)
    assert signature(FileRunStateStore.append) == signature(RunStateStore.append)
    assert signature(FileRunStateStore.status_of) == signature(RunStateStore.status_of)
    assert not hasattr(FileRunStateStore, "lookup")
    assert not hasattr(FileRunStateStore, "write_atomically")
    assert not hasattr(FileRunStateStore, "commit_bundle")


def test_each_lifecycle_record_persists_its_common_required_fields(tmp_path: Path) -> None:
    store = _store(tmp_path)
    stage, cell_id, fingerprint, timestamp = _fields()
    for record in _records():
        store.append(record)

    entries = tuple(
        msgspec.json.decode(line, type=LifecycleLogEntry)
        for line in (tmp_path / "lifecycle.jsonl").read_bytes().splitlines()
    )
    assert tuple(entry.sequence for entry in entries) == (1, 2, 3, 4, 5, 6)
    assert all(entry.stage is stage and entry.cell_id == cell_id for entry in entries)
    assert all(entry.stage_fingerprint == fingerprint and entry.timestamp == timestamp for entry in entries)


def test_failure_lifecycle_entry_preserves_its_error_family(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for record in _records():
        store.append(record)

    entries = tuple(
        msgspec.json.decode(line, type=LifecycleLogEntry)
        for line in (tmp_path / "lifecycle.jsonl").read_bytes().splitlines()
    )
    assert entries[4].error_family == "CudaOutOfMemoryError"
    assert all(entry.error_family is None for index, entry in enumerate(entries) if index != 4)


def test_status_of_uses_append_sequence_when_timestamps_collide(tmp_path: Path) -> None:
    store = _store(tmp_path)
    stage, cell_id, fingerprint, timestamp = _fields()
    store.append(StageStartRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp))
    store.append(StageBlockRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp))
    store.append(StageRecoveryRecord(stage=stage, cell_id=cell_id, stage_fingerprint=fingerprint, timestamp=timestamp))

    assert store.status_of(fingerprint) is RunStatus.RECOVERED
    assert store.status_of(StageFingerprint(value="b" * 64)) is RunStatus.PLANNED
