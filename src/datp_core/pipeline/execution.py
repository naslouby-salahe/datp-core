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

    def __post_init__(self) -> None:
        completed_stage_ids = tuple(item.stage for item in self.stages)
        expected_prefix = PIPELINE_SEQUENCE[: len(completed_stage_ids)]
        if completed_stage_ids != expected_prefix:
            raise ValueError("pipeline stages must execute in canonical order")

    @property
    def successful(self) -> bool:
        return bool(self.stages) and len(self.stages) == len(PIPELINE_SEQUENCE) and all(
            item.outcome in {StageOutcome.COMPLETED, StageOutcome.REUSED} for item in self.stages
        )


class StageRunner(Protocol):
    def run(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution: ...


class IncompleteExperimentCleaner(Protocol):
    def remove(self, coordinate: ExperimentCoordinate, output_root: Path) -> None: ...


def execute_experiment(
    *,
    coordinate: ExperimentCoordinate,
    stage_runner: StageRunner,
    cleaner: IncompleteExperimentCleaner,
    output_root: Path,
) -> ExperimentExecution:
    cleaner.remove(coordinate, output_root)
    executions: list[StageExecution] = []
    for stage in PIPELINE_SEQUENCE:
        result = stage_runner.run(stage, coordinate)
        if result.stage is not stage:
            raise ValueError("stage runner returned a result for the wrong stage")
        executions.append(result)
        if result.outcome in {StageOutcome.BLOCKED, StageOutcome.FAILED}:
            break
    return ExperimentExecution(coordinate=coordinate, stages=tuple(executions))
