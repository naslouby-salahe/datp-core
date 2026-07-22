"""Domain outcome records and tagged unions for stage execution results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .artifacts import ArtifactKey
from .identifiers import ExperimentId, JobId, PopulationId, ThresholdPolicyId


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
class StageJobContext:
    """Immutable identity context carried by every DAG job.

    Handlers must read typed fields rather than parse job_id or artifact_id strings.
    """

    experiment_id: ExperimentId
    seed: int | None = None
    evaluation_label: str | None = None
    population_id: PopulationId | None = None
    threshold_policy_id: ThresholdPolicyId | None = None
    dataset_setup_id: str | None = None
    materialization_id: str | None = None
    partition_condition: str | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    federated_summary_fixed_k: float | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJob:
    job_id: JobId
    stage: StageKind
    context: StageJobContext
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

    @classmethod
    def succeeded(cls, *, job_id: JobId, stage: StageKind, produced_artifact: ArtifactKey) -> StageJobOutcome:
        if produced_artifact is None:
            raise ValueError("A succeeded outcome must have a produced artifact")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SUCCESS, produced_artifact=produced_artifact)

    @classmethod
    def reused(cls, *, job_id: JobId, stage: StageKind, produced_artifact: ArtifactKey) -> StageJobOutcome:
        if produced_artifact is None:
            raise ValueError("A reused outcome must have a produced artifact")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.REUSED, produced_artifact=produced_artifact)

    @classmethod
    def failed(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A failed outcome must carry an error message")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.FAILED, error_message=error_message)

    @classmethod
    def skipped(cls, *, job_id: JobId, stage: StageKind, error_message: str | None = None) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SKIPPED, error_message=error_message)

    @classmethod
    def suppressed(cls, *, job_id: JobId, stage: StageKind, error_message: str | None = None) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SUPPRESSED, error_message=error_message)
