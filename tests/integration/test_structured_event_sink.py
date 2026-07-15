import json
from io import StringIO
from threading import Event
from time import sleep

from datp_core.application.ports.telemetry import (
    EventContext,
    LogEventKind,
    LogFormat,
    LogSink,
    StageLifecycleDetail,
    StructuredEvent,
)
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.runtime.policies import PipelineStage, RunStatus, WorkerRole
from datp_core.infrastructure.telemetry.structured_events import StructlogEventSink


class _NotifyingOutput(StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.written = Event()

    def write(self, value: str) -> int:
        result = super().write(value)
        self.written.set()
        return result


def _event(*, worker_role: WorkerRole, process_id: int) -> StructuredEvent:
    return StructuredEvent(
        kind=LogEventKind.STAGE_STARTED,
        context=EventContext(
            run_id="synthetic-run",
            experiment_id=None,
            cell_id=CellId(value="E-C1#0123456789abcdef"),
            stage=PipelineStage.TRAIN,
            stage_fingerprint=None,
            seed=None,
            worker_role=worker_role,
            process_id=process_id,
            gpu_index=None,
            elapsed_seconds=0.0,
            peak_ram_bytes=None,
            peak_vram_bytes=None,
        ),
        detail=StageLifecycleDetail(
            stage=PipelineStage.TRAIN,
            previous_status=RunStatus.READY,
            current_status=RunStatus.RUNNING,
        ),
        status=RunStatus.RUNNING,
        error_code=None,
        message="synthetic stage started",
    )


def test_synthetic_jsonl_events_preserve_worker_attribution() -> None:
    output = _NotifyingOutput()
    sink = StructlogEventSink(sink=LogSink.JSONL_FILE, format=LogFormat.JSON, output=output)
    sink.publish(_event(worker_role=WorkerRole.CPU_WORKER, process_id=11))
    sink.publish(_event(worker_role=WorkerRole.GPU_WORKER, process_id=22))
    assert output.written.wait(timeout=1.0)

    records = ()
    for _ in range(100):
        records = tuple(json.loads(line) for line in output.getvalue().splitlines())
        if len(records) == 2:
            break
        sleep(0.01)

    assert len(records) == 2

    assert tuple((record["worker_role"], record["process_id"]) for record in records) == (
        ("cpu_worker", 11),
        ("gpu_worker", 22),
    )
