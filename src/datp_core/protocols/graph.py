"""Immutable scientific graph-observation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.domain.values import Checksum, Seed


class GraphCoordinate(Protocol):
    """Scientific identity exposed to observation-only graph extensions."""

    @property
    def experiment(self) -> ExperimentId: ...

    @property
    def evidence_role(self) -> EvidenceRole: ...

    @property
    def dataset(self) -> DatasetId: ...

    @property
    def population(self) -> PopulationId: ...

    @property
    def training_model(self) -> TrainingModelId: ...

    @property
    def training_seed(self) -> Seed: ...

    @property
    def split_protocol(self) -> SplitProtocolId: ...

    @property
    def threshold_method(self) -> FederatedThresholdMethod: ...

    @property
    def metric(self) -> MetricId: ...

    @property
    def temporal_state(self) -> TemporalState | None: ...


class ObservationBoundary(StrEnum):
    AFTER_SCORE_GENERATION_BEFORE_CALIBRATION = "after_score_generation_before_calibration"
    AFTER_CALIBRATION_BEFORE_THRESHOLD_CONSTRUCTION = "after_calibration_before_threshold_construction"
    AFTER_THRESHOLD_CONSTRUCTION_BEFORE_EVALUATION = "after_threshold_construction_before_evaluation"
    AFTER_EVALUATION_BEFORE_ANALYSIS = "after_evaluation_before_analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationContext:
    boundary: ObservationBoundary
    coordinate: GraphCoordinate
    input_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationResult:
    boundary: ObservationBoundary
    coordinate: GraphCoordinate
    input_checksum: Checksum
    output_checksum: Checksum

    def __post_init__(self) -> None:
        if self.input_checksum != self.output_checksum:
            raise ValueError("observation hooks cannot alter scientific artifacts")


class ObservationHook(Protocol):
    def observe(self, context: ObservationContext) -> ObservationResult: ...


@dataclass(frozen=True, slots=True)
class IdentityObservationHook:
    def observe(self, context: ObservationContext) -> ObservationResult:
        return ObservationResult(
            boundary=context.boundary,
            coordinate=context.coordinate,
            input_checksum=context.input_checksum,
            output_checksum=context.input_checksum,
        )


def observe_graph_boundary(
    context: ObservationContext,
    hook: ObservationHook | None,
) -> ObservationResult:
    selected_hook = hook if hook is not None else IdentityObservationHook()
    result = selected_hook.observe(context)
    if result.boundary is not context.boundary or result.coordinate != context.coordinate:
        raise ValueError("observation hook changed its scientific boundary or coordinate")
    if result.input_checksum != context.input_checksum or result.output_checksum != context.input_checksum:
        raise ValueError("observation hook changed a scientific artifact identity")
    return result
