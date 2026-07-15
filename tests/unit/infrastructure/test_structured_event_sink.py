from inspect import signature
from io import StringIO
from threading import Event
from time import monotonic

import pytest

from datp_core.application.ports.telemetry import (
    EventContext,
    EventSink,
    LogEventKind,
    LogFormat,
    LogSink,
    StageLifecycleDetail,
    StructuredEvent,
)
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.runtime.policies import PipelineStage, RunStatus, WorkerRole
from datp_core.infrastructure.telemetry import structured_events
from datp_core.infrastructure.telemetry.structured_events import StructlogEventSink


class _BrokenOutput(StringIO):
    def write(self, value: str) -> int:
        del value
        raise OSError("synthetic broken telemetry sink")

    def flush(self) -> None:
        raise OSError("synthetic broken telemetry sink")


class _NotifyingOutput(StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.written = Event()

    def write(self, value: str) -> int:
        result = super().write(value)
        self.written.set()
        return result


class _BlockedOutput(StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()

    def write(self, value: str) -> int:
        self.started.set()
        assert self.release.wait(timeout=1.0)
        return super().write(value)


class _FailureLogger:
    def __init__(self) -> None:
        self.reported = Event()
        self.count = 0

    def error(self, message: str) -> None:
        assert message == "telemetry rendering failed"
        self.count += 1
        self.reported.set()


def _wait_for_output(output: _NotifyingOutput) -> str:
    assert output.written.wait(timeout=1.0)
    return output.getvalue()


def _event(*, worker_role: WorkerRole = WorkerRole.MAIN, process_id: int = 1) -> StructuredEvent:
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


def test_structlog_sink_matches_the_event_sink_contract() -> None:
    assert signature(StructlogEventSink.publish) == signature(EventSink.publish)


def test_rendering_failure_is_best_effort_and_reported_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _FailureLogger()

    def failure_logger(_: str | None = None) -> _FailureLogger:
        return logger

    monkeypatch.setattr(structured_events.structlog, "get_logger", failure_logger)
    sink = StructlogEventSink(sink=LogSink.CONSOLE, format=LogFormat.HUMAN_READABLE, output=_BrokenOutput())

    sink.publish(_event())
    assert logger.reported.wait(timeout=1.0)
    assert logger.count == 1


def test_blocked_rendering_never_stalls_the_publishing_stage() -> None:
    output = _BlockedOutput()
    sink = StructlogEventSink(sink=LogSink.CONSOLE, format=LogFormat.HUMAN_READABLE, output=output)

    started = monotonic()
    sink.publish(_event())

    assert monotonic() - started < 0.05
    assert output.started.wait(timeout=1.0)
    output.release.set()


def test_human_readable_rendering_includes_the_typed_event_context() -> None:
    output = _NotifyingOutput()
    StructlogEventSink(sink=LogSink.CONSOLE, format=LogFormat.HUMAN_READABLE, output=output).publish(_event())

    rendered = _wait_for_output(output)
    assert "synthetic stage started" in rendered
    assert "worker_role=main" in rendered
    assert "process_id=1" in rendered
