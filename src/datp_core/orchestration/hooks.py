"""Immutable observation-only extension boundaries and Dagster failure logging."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from dagster import HookContext, failure_hook

from datp_core.domain.values import Checksum
from datp_core.pipeline.planning import ExperimentCoordinate


class ObservationBoundary(StrEnum):
    BEFORE_CALIBRATION = "before_calibration"
    BEFORE_THRESHOLD_CONSTRUCTION = "before_threshold_construction"
    BEFORE_EVALUATION = "before_evaluation"
    BEFORE_ANALYSIS = "before_analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationContext:
    boundary: ObservationBoundary
    coordinate: ExperimentCoordinate
    input_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationResult:
    boundary: ObservationBoundary
    coordinate: ExperimentCoordinate
    input_checksum: Checksum
    output_checksum: Checksum

    def __post_init__(self) -> None:
        if self.input_checksum != self.output_checksum:
            raise ValueError("observation hooks cannot alter scientific artifacts")


class ObservationHook(Protocol):
    def observe(self, context: ObservationContext) -> ObservationResult: ...


@dataclass(frozen=True, slots=True)
class NoOpObservationHook:
    def observe(self, context: ObservationContext) -> ObservationResult:
        return ObservationResult(
            boundary=context.boundary,
            coordinate=context.coordinate,
            input_checksum=context.input_checksum,
            output_checksum=context.input_checksum,
        )


def apply_observation_hook(context: ObservationContext, hook: ObservationHook | None) -> ObservationResult:
    selected_hook = hook if hook is not None else NoOpObservationHook()
    result = selected_hook.observe(context)
    if result.boundary is not context.boundary or result.coordinate != context.coordinate:
        raise ValueError("observation hook changed its scientific boundary or coordinate")
    if result.input_checksum != context.input_checksum or result.output_checksum != context.input_checksum:
        raise ValueError("observation hook changed a scientific artifact identity")
    return result


@failure_hook
def log_pipeline_failure(context: HookContext) -> None:
    context.log.error(f"DATP-Core pipeline step failed: {context.op.name}")
