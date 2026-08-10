"""Console and durable-log progress reporting for programme execution."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from datp_core.experiments.execution.models import (
    PipelineStage,
    ProgressEvent,
    ProgressEventKind,
    ProgressHook,
    StageOutcome,
)


def _require_int(value: int | None, kind: str) -> int:
    if value is None:
        raise ValueError(f"{kind} progress event requires a numeric value")
    return value


def _require_outcome(value: StageOutcome | None, kind: str) -> StageOutcome:
    if value is None:
        raise ValueError(f"{kind} progress event requires a stage outcome")
    return value


def _require_stage(value: PipelineStage | None, kind: str) -> PipelineStage:
    if value is None:
        raise ValueError(f"{kind} progress event requires a stage")
    return value


def format_progress_event(event: ProgressEvent) -> str:
    """Render one observation-only progress event as a plain single-line report."""
    coordinate = event.coordinate
    identity = (
        f"{coordinate.experiment.value} seed={coordinate.training_seed.value} "
        f"{coordinate.dataset.value}:{coordinate.population.value} method={coordinate.threshold_method.value}"
        if coordinate is not None
        else ""
    )
    if event.kind is ProgressEventKind.CAMPAIGN_BEGIN:
        return f"campaign begin coordinates={event.total}"
    if event.kind is ProgressEventKind.CAMPAIGN_END:
        return f"campaign end {event.detail}"
    if event.kind is ProgressEventKind.COORDINATE_BEGIN:
        total = _require_int(event.total, event.kind.value)
        return f"coordinate {_require_int(event.ordinal, event.kind.value)}/{total} begin {identity}"
    if event.kind is ProgressEventKind.COORDINATE_END:
        total = _require_int(event.total, event.kind.value)
        reuse = " reused" if event.reused else ""
        elapsed = f" elapsed={event.elapsed_seconds:.1f}s" if event.elapsed_seconds is not None else ""
        return (
            f"coordinate {_require_int(event.ordinal, event.kind.value)}/{total} end {identity}{reuse}"
            f"{elapsed} {event.detail}"
        )
    if event.kind is ProgressEventKind.STAGE_BEGIN:
        return f"  stage {_require_stage(event.stage, event.kind.value).value} begin {identity}"
    if event.kind is ProgressEventKind.STAGE_END:
        elapsed = f" elapsed={event.elapsed_seconds:.1f}s" if event.elapsed_seconds is not None else ""
        return (
            f"  stage {_require_stage(event.stage, event.kind.value).value} end "
            f"outcome={_require_outcome(event.outcome, event.kind.value).value}{elapsed}"
        )
    round_number = _require_int(event.round_number, event.kind.value)
    maximum_round = _require_int(event.maximum_round, event.kind.value)
    return f"    round {round_number}/{maximum_round}"


class ConsoleProgressHook:
    """Emit progress to a text stream and append each line to a durable log."""

    def __init__(self, output: TextIO, log_path: Path | None = None) -> None:
        self.output = output
        self.log_path = log_path
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_round: dict[str, int] = {}

    def emit(self, event: ProgressEvent) -> None:
        if event.kind is ProgressEventKind.TRAINING_ROUND and not self._show_round(event):
            return
        line = format_progress_event(event)
        print(line, file=self.output, flush=True)
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{event.kind.value} {line}\n")

    def _show_round(self, event: ProgressEvent) -> bool:
        if event.coordinate is None or event.round_number is None or event.maximum_round is None:
            return False
        key = event.coordinate.stable_key
        previous = self._last_round.get(key, 0)
        if event.round_number <= previous:
            return False
        emit = event.round_number == 1 or event.round_number == event.maximum_round or event.round_number % 10 == 0
        if emit:
            self._last_round[key] = event.round_number
        return emit


def progress_hook(output: TextIO, log_path: Path | None) -> ProgressHook:
    return ConsoleProgressHook(output=output, log_path=log_path)
