"""Stage job outcomes with constructor-guaranteed invariants."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.artifacts.identity import ArtifactKey
from datp_core.core.identifiers import JobId
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJobOutcome:
    job_id: JobId
    stage: StageKind
    status: JobExecutionStatus
    produced_artifact: ArtifactKey | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _validate_outcome_invariants(self)

    @classmethod
    def succeeded(cls, *, job_id: JobId, stage: StageKind, produced_artifact: ArtifactKey) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SUCCESS, produced_artifact=produced_artifact)

    @classmethod
    def reused(cls, *, job_id: JobId, stage: StageKind, produced_artifact: ArtifactKey) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.REUSED, produced_artifact=produced_artifact)

    @classmethod
    def failed(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A failed outcome must carry a non-empty error message")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.FAILED, error_message=error_message)

    @classmethod
    def skipped(cls, *, job_id: JobId, stage: StageKind, error_message: str | None = None) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SKIPPED, error_message=error_message)

    @classmethod
    def suppressed(cls, *, job_id: JobId, stage: StageKind, error_message: str | None = None) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SUPPRESSED, error_message=error_message)

    @classmethod
    def infeasible(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("An infeasible outcome must carry a non-empty error message")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.INFEASIBLE, error_message=error_message)

    @classmethod
    def blocked_by_dependency(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A blocked-by-dependency outcome must carry a non-empty error message")
        return cls(
            job_id=job_id, stage=stage, status=JobExecutionStatus.BLOCKED_BY_DEPENDENCY, error_message=error_message
        )


def _validate_outcome_invariants(outcome: StageJobOutcome) -> None:
    status = outcome.status
    has_artifact = outcome.produced_artifact is not None
    has_message = outcome.error_message is not None and outcome.error_message != ""

    if status in (JobExecutionStatus.SUCCESS, JobExecutionStatus.REUSED):
        if not has_artifact:
            raise ValueError(f"{status.value} outcome requires a produced artifact")
        if has_message:
            raise ValueError(f"{status.value} outcome must not carry an error message")

    if status in (JobExecutionStatus.FAILED, JobExecutionStatus.INFEASIBLE, JobExecutionStatus.BLOCKED_BY_DEPENDENCY):
        if not has_message:
            raise ValueError(f"{status.value} outcome requires a non-empty error message")
        if has_artifact:
            raise ValueError(f"{status.value} outcome must not carry a produced artifact")
