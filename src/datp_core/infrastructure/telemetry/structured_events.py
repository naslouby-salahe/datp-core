from dataclasses import dataclass
from queue import Full, Queue
from threading import Lock, Thread
from typing import TextIO, TypeGuard, assert_never

import msgspec
import structlog

from datp_core.application.ports.telemetry import EventDetail, LogFormat, LogSink, StructuredEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class _RenderRequest:
    sink: LogSink
    format: LogFormat
    output: TextIO
    event: StructuredEvent


_RENDER_QUEUE: Queue[_RenderRequest] = Queue(maxsize=1024)
_RENDER_WORKER_LOCK = Lock()
_render_worker_started = False


@dataclass(frozen=True, slots=True, kw_only=True)
class StructlogEventSink:
    sink: LogSink
    format: LogFormat
    output: TextIO

    def publish(self, event: StructuredEvent) -> None:
        _ensure_render_worker()
        try:
            _RENDER_QUEUE.put_nowait(
                _RenderRequest(sink=self.sink, format=self.format, output=self.output, event=event)
            )
        except Full:
            return


def _ensure_render_worker() -> None:
    global _render_worker_started
    if _render_worker_started:
        return
    with _RENDER_WORKER_LOCK:
        if _render_worker_started:
            return
        Thread(target=_render_worker, name="datp-telemetry-renderer", daemon=True).start()
        _render_worker_started = True


def _renderer(format: LogFormat) -> structlog.types.Processor:
    match format:
        case LogFormat.HUMAN_READABLE:
            return structlog.dev.ConsoleRenderer(colors=False)
        case LogFormat.JSON:
            return structlog.processors.JSONRenderer()
        case _ as unreachable:
            assert_never(unreachable)


def _context(event: StructuredEvent) -> dict[str, object]:
    context = event.context
    return {
        "run_id": context.run_id,
        "experiment_id": None if context.experiment_id is None else context.experiment_id.value,
        "cell_id": None if context.cell_id is None else context.cell_id.value,
        "stage": None if context.stage is None else context.stage.value,
        "stage_fingerprint": None if context.stage_fingerprint is None else context.stage_fingerprint.value,
        "seed": None if context.seed is None else context.seed.value,
        "worker_role": context.worker_role.value,
        "process_id": context.process_id,
        "gpu_index": None if context.gpu_index is None else context.gpu_index.value,
        "elapsed_seconds": context.elapsed_seconds,
        "peak_ram_bytes": context.peak_ram_bytes,
        "peak_vram_bytes": context.peak_vram_bytes,
        "status": None if event.status is None else event.status.value,
        "error_code": event.error_code,
    }


def _render_worker() -> None:
    while True:
        request = _RENDER_QUEUE.get()
        try:
            _render(request)
        finally:
            _RENDER_QUEUE.task_done()


def _render(request: _RenderRequest) -> None:
    try:
        detail = _detail_payload(request.event.detail)
        if not _is_permitted_payload(detail):
            return
        logger = structlog.wrap_logger(
            structlog.PrintLoggerFactory(file=request.output)(),
            processors=(_renderer(request.format),),
        ).bind(log_sink=request.sink.value, **_context(request.event))
        logger.info(request.event.message, event_kind=request.event.kind.value, detail=detail)
    except Exception:
        _report_rendering_failure()


def _detail_payload(detail: EventDetail) -> object:
    return msgspec.to_builtins(detail)


def _is_permitted_payload(value: object) -> bool:
    match value:
        case None | str() | int() | float() | bool():
            return True
        case _:
            return _is_permitted_mapping(value) if _is_object_mapping(value) else False


def _is_object_mapping(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _is_permitted_mapping(value: dict[object, object]) -> bool:
    return all(
        isinstance(key, str)
        and "secret" not in key.lower()
        and ("config" not in key.lower() or key == "resolved_configuration")
        and _is_permitted_payload(item)
        for key, item in value.items()
    )


def _report_rendering_failure() -> None:
    try:
        structlog.get_logger(__name__).error("telemetry rendering failed")
    except Exception:
        return
