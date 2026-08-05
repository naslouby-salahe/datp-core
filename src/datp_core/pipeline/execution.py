"""Canonical experiment execution order and reusable execution contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from datp_core.pipeline.planning import ExperimentCoordinate


class PipelineStage(StrEnum):
    MATERIALIZE_DATASET = "materialize_dataset"
    CONSTRUCT_POPULATION = "construct_population"
    FIT_PREPROCESSING = "fit_preprocessing"
    TRAIN_DETECTOR = "train_detector"
    SELECT_CHECKPOINT = "select_checkpoint"
    GENERATE_SCORES = "generate_scores"
    BUILD_CALIBRATION = "build_calibration"
    CONSTRUCT_THRESHOLDS = "construct_thresholds"
    EVALUATE_DETECTOR = "evaluate_detector"
    ANALYZE_EVIDENCE = "analyze_evidence"
    VERIFY_ANCHOR = "verify_anchor"
    PUBLISH_REPORT = "publish_report"


PIPELINE_SEQUENCE = tuple(PipelineStage)


class StageOutcome(StrEnum):
    COMPLETED = "completed"
    REUSED = "reused"
    BLOCKED = "blocked"
    FAILED = "failed"


class ExistingExperimentState(StrEnum):
    ABSENT = "absent"
    COMPLETE_VALID = "complete_valid"
    COMPLETE_INVALID = "complete_invalid"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True, kw_only=True)
class StageExecution:
    stage: PipelineStage
    outcome: StageOutcome
    evidence: str

    def __post_init__(self) -> None:
        if not self.evidence.strip():
            raise ValueError("stage execution requires evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentExecution:
    coordinate: ExperimentCoordinate
    stages: tuple[StageExecution, ...]
    reused_complete_experiment: bool = False

    def __post_init__(self) -> None:
        completed_stage_ids = tuple(item.stage for item in self.stages)
        expected_prefix = PIPELINE_SEQUENCE[: len(completed_stage_ids)]
        if completed_stage_ids != expected_prefix:
            raise ValueError("pipeline stages must execute in canonical order")
        if self.reused_complete_experiment and self.stages:
            raise ValueError("a reused complete experiment must not execute stages")

    @property
    def successful(self) -> bool:
        if self.reused_complete_experiment:
            return True
        return (
            bool(self.stages)
            and len(self.stages) == len(PIPELINE_SEQUENCE)
            and all(item.outcome in {StageOutcome.COMPLETED, StageOutcome.REUSED} for item in self.stages)
        )


class StageRunner(Protocol):
    def run(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution: ...


class ExperimentOutputStore(Protocol):
    def state(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExistingExperimentState: ...

    def delete(self, coordinate: ExperimentCoordinate, output_root: Path) -> None: ...


def execute_experiment(
    *,
    coordinate: ExperimentCoordinate,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root: Path,
    overwrite: bool = False,
) -> ExperimentExecution:
    existing_state = output_store.state(coordinate, output_root)
    if overwrite:
        if existing_state is not ExistingExperimentState.ABSENT:
            output_store.delete(coordinate, output_root)
    elif existing_state is ExistingExperimentState.COMPLETE_VALID:
        return ExperimentExecution(
            coordinate=coordinate,
            stages=(),
            reused_complete_experiment=True,
        )
    elif existing_state is ExistingExperimentState.COMPLETE_INVALID:
        raise ValueError("completed experiment failed publication validation")
    elif existing_state is ExistingExperimentState.INCOMPLETE:
        output_store.delete(coordinate, output_root)

    executions: list[StageExecution] = []
    for stage in PIPELINE_SEQUENCE:
        result = stage_runner.run(stage, coordinate)
        if result.stage is not stage:
            raise ValueError("stage runner returned a result for the wrong stage")
        executions.append(result)
        if result.outcome in {StageOutcome.BLOCKED, StageOutcome.FAILED}:
            break
    return ExperimentExecution(coordinate=coordinate, stages=tuple(executions))
