"""Domain outcome records and tagged unions for stage execution results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .artifacts import ArtifactKey
from .identifiers import JobId


class StageKind(Enum):
    PREFLIGHT = "preflight"
    DATASET_MATERIALIZATION = "dataset_materialization"
    MODEL_TRAINING = "model_training"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    SCORE_GENERATION = "score_generation"
    THRESHOLD_CONSTRUCTION = "threshold_construction"
    OPERATING_POINT_EVALUATION = "operating_point_evaluation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    REPORT_GENERATION = "report_generation"
    RESULT_FREEZE = "result_freeze"


class JobExecutionStatus(Enum):
    SUCCESS = "success"
    REUSED = "reused"
    SKIPPED = "skipped"
    SUPPRESSED = "suppressed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJob:
    job_id: JobId
    stage: StageKind
    inputs: tuple[ArtifactKey, ...]
    output: ArtifactKey
    dependencies: tuple[JobId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJobOutcome:
    job_id: JobId
    stage: StageKind
    status: JobExecutionStatus
    produced_artifact: ArtifactKey | None = None
    error_message: str | None = None
