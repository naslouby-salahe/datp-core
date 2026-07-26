"""Authoritative stage kinds and job execution statuses."""

from __future__ import annotations

from enum import Enum, StrEnum


class StageKind(StrEnum):
    PREFLIGHT = "preflight"
    DATASET_MATERIALIZATION = "dataset_materialization"
    MODEL_TRAINING = "model_training"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    SCORE_GENERATION = "score_generation"
    CALIBRATION_SUBSAMPLING = "calibration_subsampling"
    THRESHOLD_CONSTRUCTION = "threshold_construction"
    OPERATING_POINT_EVALUATION = "operating_point_evaluation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    REPORT_GENERATION = "report_generation"
    RESULT_FREEZE = "result_freeze"


class JobExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    INFEASIBLE = "infeasible"
    BLOCKED_BY_DEPENDENCY = "blocked_by_dependency"


DEPENDENCY_SATISFYING_STATUSES: frozenset[JobExecutionStatus] = frozenset(
    {JobExecutionStatus.SUCCESS})
