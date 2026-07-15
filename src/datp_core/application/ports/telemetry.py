from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from datp_core.domain.artifacts.references import ArtifactRef, StageFingerprint
from datp_core.domain.experiments.identities import CellId, ExperimentId
from datp_core.domain.runtime.admissibility import GpuIndex
from datp_core.domain.runtime.policies import PipelineStage, RunStatus, WorkerRole
from datp_core.domain.runtime.seeds import Seed


class LogEventKind(StrEnum):
    RUN_PLANNED = "run_planned"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    STAGE_STARTED = "stage_started"
    STAGE_REUSED = "stage_reused"
    STAGE_COMPLETED = "stage_completed"
    STAGE_BLOCKED = "stage_blocked"
    STAGE_FAILED = "stage_failed"
    STAGE_HEARTBEAT = "stage_heartbeat"
    FEDERATED_ROUND_STARTED = "federated_round_started"
    FEDERATED_ROUND_COMPLETED = "federated_round_completed"
    FEDERATED_ROUND_FAILED = "federated_round_failed"
    RECOVERY_CHECKPOINT_COMMITTED = "recovery_checkpoint_committed"
    RESOURCE_PRESSURE_DETECTED = "resource_pressure_detected"
    STAGE_PAUSED = "stage_paused"
    STAGE_RESUMED = "stage_resumed"
    ARTIFACT_LOCK_ACQUIRED = "artifact_lock_acquired"
    ARTIFACT_REUSED = "artifact_reused"
    ARTIFACT_WRITTEN = "artifact_written"
    ARTIFACT_REJECTED = "artifact_rejected"
    RESOURCE_PREFLIGHT_COMPLETED = "resource_preflight_completed"
    CUDA_OUT_OF_MEMORY = "cuda_out_of_memory"
    DETERMINISM_VIOLATION = "determinism_violation"
    LINEAGE_MISMATCH = "lineage_mismatch"
    TEST_PROFILE_STARTED = "test_profile_started"
    TEST_PROFILE_COMPLETED = "test_profile_completed"


class LogSink(StrEnum):
    CONSOLE = "console"
    JSONL_FILE = "jsonl_file"


class LogFormat(StrEnum):
    HUMAN_READABLE = "human_readable"
    JSON = "json"


@dataclass(frozen=True, slots=True, kw_only=True)
class EventContext:
    run_id: str
    experiment_id: ExperimentId | None
    cell_id: CellId | None
    stage: PipelineStage | None
    stage_fingerprint: StageFingerprint | None
    seed: Seed | None
    worker_role: WorkerRole
    process_id: int
    gpu_index: GpuIndex | None
    elapsed_seconds: float
    peak_ram_bytes: int | None
    peak_vram_bytes: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class RunPlannedDetail:
    resolved_configuration: ArtifactRef
    planned_stage_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class StageLifecycleDetail:
    stage: PipelineStage
    previous_status: RunStatus | None
    current_status: RunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactEventDetail:
    artifact: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceEventDetail:
    available_ram_bytes: int | None
    available_vram_bytes: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class DeterminismEventDetail:
    expected_seed: Seed
    observed_seed: Seed | None


@dataclass(frozen=True, slots=True, kw_only=True)
class LineageEventDetail:
    expected_fingerprint: StageFingerprint
    observed_fingerprint: StageFingerprint | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedRoundEventDetail:
    round_number: int
    expected_client_count: int
    completed_client_count: int
    failed_client_count: int
    duration_seconds: float
    peak_ram_bytes: int | None
    peak_vram_bytes: int | None
    recovery_status: RunStatus | None


@dataclass(frozen=True, slots=True, kw_only=True)
class HeartbeatEventDetail:
    last_progress_stage: PipelineStage
    staleness_deadline_seconds: float


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryEventDetail:
    compatible_checkpoint: ArtifactRef
    last_completed_round: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TestProfileDetail:
    profile_name: str
    suite_name: str


type EventDetail = (
    RunPlannedDetail
    | StageLifecycleDetail
    | ArtifactEventDetail
    | ResourceEventDetail
    | DeterminismEventDetail
    | LineageEventDetail
    | FederatedRoundEventDetail
    | HeartbeatEventDetail
    | RecoveryEventDetail
    | TestProfileDetail
)

type EventDetailType = (
    type[RunPlannedDetail]
    | type[StageLifecycleDetail]
    | type[ArtifactEventDetail]
    | type[ResourceEventDetail]
    | type[DeterminismEventDetail]
    | type[LineageEventDetail]
    | type[FederatedRoundEventDetail]
    | type[HeartbeatEventDetail]
    | type[RecoveryEventDetail]
    | type[TestProfileDetail]
)


@dataclass(frozen=True, slots=True, kw_only=True)
class EventDetailBinding:
    kind: LogEventKind
    detail_type: EventDetailType


EVENT_DETAIL_BINDINGS: tuple[EventDetailBinding, ...] = (
    EventDetailBinding(kind=LogEventKind.RUN_PLANNED, detail_type=RunPlannedDetail),
    EventDetailBinding(kind=LogEventKind.RUN_STARTED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.RUN_COMPLETED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.RUN_FAILED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_STARTED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_REUSED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_COMPLETED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_BLOCKED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_FAILED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_HEARTBEAT, detail_type=HeartbeatEventDetail),
    EventDetailBinding(kind=LogEventKind.FEDERATED_ROUND_STARTED, detail_type=FederatedRoundEventDetail),
    EventDetailBinding(kind=LogEventKind.FEDERATED_ROUND_COMPLETED, detail_type=FederatedRoundEventDetail),
    EventDetailBinding(kind=LogEventKind.FEDERATED_ROUND_FAILED, detail_type=FederatedRoundEventDetail),
    EventDetailBinding(kind=LogEventKind.RECOVERY_CHECKPOINT_COMMITTED, detail_type=RecoveryEventDetail),
    EventDetailBinding(kind=LogEventKind.RESOURCE_PRESSURE_DETECTED, detail_type=ResourceEventDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_PAUSED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.STAGE_RESUMED, detail_type=StageLifecycleDetail),
    EventDetailBinding(kind=LogEventKind.ARTIFACT_LOCK_ACQUIRED, detail_type=ArtifactEventDetail),
    EventDetailBinding(kind=LogEventKind.ARTIFACT_REUSED, detail_type=ArtifactEventDetail),
    EventDetailBinding(kind=LogEventKind.ARTIFACT_WRITTEN, detail_type=ArtifactEventDetail),
    EventDetailBinding(kind=LogEventKind.ARTIFACT_REJECTED, detail_type=ArtifactEventDetail),
    EventDetailBinding(kind=LogEventKind.RESOURCE_PREFLIGHT_COMPLETED, detail_type=ResourceEventDetail),
    EventDetailBinding(kind=LogEventKind.CUDA_OUT_OF_MEMORY, detail_type=ResourceEventDetail),
    EventDetailBinding(kind=LogEventKind.DETERMINISM_VIOLATION, detail_type=DeterminismEventDetail),
    EventDetailBinding(kind=LogEventKind.LINEAGE_MISMATCH, detail_type=LineageEventDetail),
    EventDetailBinding(kind=LogEventKind.TEST_PROFILE_STARTED, detail_type=TestProfileDetail),
    EventDetailBinding(kind=LogEventKind.TEST_PROFILE_COMPLETED, detail_type=TestProfileDetail),
)


def expected_event_detail_type(kind: LogEventKind) -> EventDetailType:
    for binding in EVENT_DETAIL_BINDINGS:
        if binding.kind is kind:
            return binding.detail_type
    raise ValueError(f"unbound log event kind: {kind}")


@dataclass(frozen=True, slots=True, kw_only=True)
class StructuredEvent:
    kind: LogEventKind
    context: EventContext
    detail: EventDetail
    status: RunStatus | None
    error_code: str | None
    message: str

    def __post_init__(self) -> None:
        if type(self.detail) is not expected_event_detail_type(self.kind):
            raise ValueError(f"event detail does not match log event kind: {self.kind}")


class EventSink(Protocol):
    def publish(self, event: StructuredEvent) -> None: ...


def publish_diagnostic_event(*, event_sink: EventSink, event: StructuredEvent) -> None:
    try:
        event_sink.publish(event)
    except Exception:
        return
