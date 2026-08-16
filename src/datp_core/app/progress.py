from __future__ import annotations

from pathlib import Path
from typing import TextIO

from datp_core.core.numeric import RoundNumber
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.execution.models import (
    ProgressEvent,
    ProgressEventKind,
    ProgressHook,
)


def _require_value[T](value: T | None, kind: ProgressEventKind) -> T:
    if value is None:
        raise ValueError(f"{kind.value} progress event requires a value")
    return value


def format_progress_event(event: ProgressEvent) -> str:
    coordinate = event.coordinate
    identity = (
        f"{coordinate.experiment.value} seed={coordinate.training_seed.value} "
        f"{coordinate.dataset.value}:{coordinate.population.value} method={coordinate.threshold_method.value}"
        if coordinate is not None
        else ""
    )
    if event.kind is ProgressEventKind.CAMPAIGN_BEGIN:
        return f"campaign begin coordinates={_require_value(event.total, event.kind).value}"
    if event.kind is ProgressEventKind.CAMPAIGN_END:
        return f"campaign end {_require_value(event.detail, event.kind)}"
    if event.kind is ProgressEventKind.COORDINATE_BEGIN:
        total = _require_value(event.total, event.kind)
        ordinal = _require_value(event.ordinal, event.kind)
        return f"coordinate {ordinal.value}/{total.value} begin {identity}"
    if event.kind is ProgressEventKind.COORDINATE_END:
        total = _require_value(event.total, event.kind)
        ordinal = _require_value(event.ordinal, event.kind)
        elapsed = f" elapsed={event.elapsed_seconds.value:.1f}s" if event.elapsed_seconds is not None else ""
        detail = _require_value(event.detail, event.kind)
        return f"coordinate {ordinal.value}/{total.value} end {identity}{elapsed} {detail}"
    if event.kind is ProgressEventKind.STAGE_BEGIN:
        return f"  stage {_require_value(event.stage, event.kind).value} begin {identity}"
    if event.kind is ProgressEventKind.STAGE_END:
        elapsed = f" elapsed={event.elapsed_seconds.value:.1f}s" if event.elapsed_seconds is not None else ""
        detail = f" detail={event.detail}" if event.detail is not None else ""
        return (
            f"  stage {_require_value(event.stage, event.kind).value} end "
            f"outcome={_require_value(event.outcome, event.kind).value}{elapsed}{detail}"
        )
    round_number = _require_value(event.round_number, event.kind)
    maximum_round = _require_value(event.maximum_round, event.kind)
    return f"    round {round_number.value}/{maximum_round.value}"


class ConsoleProgressHook:
    def __init__(self, output: TextIO, log_path: Path | None = None) -> None:
        self.output = output
        self.log_path = log_path
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_round: dict[ExperimentCoordinate, RoundNumber] = {}

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
        key = event.coordinate
        previous = self._last_round.get(key)
        if previous is not None and event.round_number.value <= previous.value:
            return False
        emit = (
            event.round_number.value == 1
            or event.round_number == event.maximum_round
            or event.round_number.value % 10 == 0
        )
        if emit:
            self._last_round[key] = event.round_number
        return emit


def progress_hook(output: TextIO, log_path: Path | None) -> ProgressHook:
    return ConsoleProgressHook(output=output, log_path=log_path)
