from dataclasses import dataclass
from datetime import datetime
from os import fsync
from pathlib import Path
from typing import assert_never

import msgspec
from filelock import FileLock

from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.runtime.policies import PipelineStage, RunStatus
from datp_core.infrastructure.persistence.roots import BoundStorageRoot


@dataclass(frozen=True, slots=True, kw_only=True)
class StageStartRecord:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_record_fields(self.stage, self.cell_id, self.stage_fingerprint, self.timestamp)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageCompletionRecord:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_record_fields(self.stage, self.cell_id, self.stage_fingerprint, self.timestamp)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageReuseRecord:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_record_fields(self.stage, self.cell_id, self.stage_fingerprint, self.timestamp)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageBlockRecord:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_record_fields(self.stage, self.cell_id, self.stage_fingerprint, self.timestamp)


@dataclass(frozen=True, slots=True, kw_only=True)
class StageFailureRecord:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime
    error_family: str

    def __post_init__(self) -> None:
        _validate_record_fields(self.stage, self.cell_id, self.stage_fingerprint, self.timestamp)
        if not self.error_family:
            raise ValueError("stage failure records require a non-empty error family")


@dataclass(frozen=True, slots=True, kw_only=True)
class StageRecoveryRecord:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_record_fields(self.stage, self.cell_id, self.stage_fingerprint, self.timestamp)


type LifecycleRecord = (
    StageStartRecord
    | StageCompletionRecord
    | StageReuseRecord
    | StageBlockRecord
    | StageFailureRecord
    | StageRecoveryRecord
)


@dataclass(frozen=True, slots=True, kw_only=True)
class LifecycleJournalEntry:
    sequence: int
    status: RunStatus
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    timestamp: datetime
    error_family: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FileRunStateStore:
    root: BoundStorageRoot

    def __post_init__(self) -> None:
        if self.root.spec.kind is not StorageRootKind.RUN_STATE:
            raise ValueError("run-state store requires the run-state root")

    def append(self, record: object) -> None:
        lifecycle_record = _require_lifecycle_record(record)
        journal_path = self.root.absolute_path / "lifecycle.jsonl"
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(journal_path.with_suffix(".lock"))):
            entry = LifecycleJournalEntry(
                sequence=_next_sequence(journal_path),
                status=_status_for(lifecycle_record),
                stage=lifecycle_record.stage,
                cell_id=lifecycle_record.cell_id,
                stage_fingerprint=lifecycle_record.stage_fingerprint,
                timestamp=lifecycle_record.timestamp,
                error_family=_error_family(lifecycle_record),
            )
            with journal_path.open("ab") as journal:
                journal.write(msgspec.json.encode(entry) + b"\n")
                journal.flush()
                fsync(journal.fileno())

    def status_of(self, stage_fingerprint: StageFingerprint) -> RunStatus:
        journal_path = self.root.absolute_path / "lifecycle.jsonl"
        if not journal_path.exists():
            return RunStatus.PLANNED
        entries = tuple(
            msgspec.json.decode(line, type=LifecycleJournalEntry) for line in journal_path.read_bytes().splitlines()
        )
        return _latest_status(entries=entries, stage_fingerprint=stage_fingerprint)


def _validate_record_fields(
    stage: PipelineStage, cell_id: CellId, stage_fingerprint: StageFingerprint, timestamp: datetime
) -> None:
    if not all(
        (
            type(stage) is PipelineStage,
            type(cell_id) is CellId,
            type(stage_fingerprint) is StageFingerprint,
        )
    ):
        raise ValueError("lifecycle records require typed stage, cell, and stage fingerprint fields")
    if type(timestamp) is not datetime or timestamp.tzinfo is None:
        raise ValueError("lifecycle records require an aware timestamp")


def _require_lifecycle_record(record: object) -> LifecycleRecord:
    record_types = (
        StageStartRecord,
        StageCompletionRecord,
        StageReuseRecord,
        StageBlockRecord,
        StageFailureRecord,
        StageRecoveryRecord,
    )
    if isinstance(record, record_types):
        return record
    raise ValueError("run-state store accepts only explicit lifecycle records")


def _status_for(record: LifecycleRecord) -> RunStatus:
    match record:
        case StageStartRecord():
            return RunStatus.RUNNING
        case StageCompletionRecord():
            return RunStatus.COMPLETED
        case StageReuseRecord():
            return RunStatus.REUSED
        case StageBlockRecord():
            return RunStatus.BLOCKED
        case StageFailureRecord():
            return RunStatus.FAILED
        case StageRecoveryRecord():
            return RunStatus.RECOVERED
        case _ as unreachable:
            assert_never(unreachable)


def _next_sequence(journal_path: Path) -> int:
    if not journal_path.exists():
        return 1
    return sum(1 for line in journal_path.read_bytes().splitlines() if line) + 1


def _latest_status(*, entries: tuple[LifecycleJournalEntry, ...], stage_fingerprint: StageFingerprint) -> RunStatus:
    matching_entries = tuple(entry for entry in entries if entry.stage_fingerprint == stage_fingerprint)
    if not matching_entries:
        return RunStatus.PLANNED
    return max(matching_entries, key=lambda entry: entry.sequence).status


def _error_family(record: LifecycleRecord) -> str | None:
    return record.error_family if isinstance(record, StageFailureRecord) else None
