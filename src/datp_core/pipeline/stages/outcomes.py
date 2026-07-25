"""Stage job outcomes with constructor-guaranteed invariants."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.jobs import StageOutput


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJobOutcome:
    node_key: GraphNodeKey
    stage: StageKind
    status: JobExecutionStatus
    produced_outputs: tuple[StageOutput, ...] = ()
    error_message: str | None = None

    def __post_init__(self) -> None:
        _validate_outcome_invariants(self)

    @classmethod
    def succeeded(
        cls, *, node_key: GraphNodeKey, stage: StageKind, produced_outputs: tuple[StageOutput, ...]
    ) -> StageJobOutcome:
        return cls(node_key=node_key, stage=stage, status=JobExecutionStatus.SUCCESS, produced_outputs=produced_outputs)

    @classmethod
    def failed(cls, *, node_key: GraphNodeKey, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A failed outcome must carry a non-empty error message")
        return cls(node_key=node_key, stage=stage, status=JobExecutionStatus.FAILED, error_message=error_message)

    @classmethod
    def infeasible(cls, *, node_key: GraphNodeKey, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("An infeasible outcome must carry a non-empty error message")
        return cls(node_key=node_key, stage=stage, status=JobExecutionStatus.INFEASIBLE, error_message=error_message)

    @classmethod
    def blocked_by_dependency(cls, *, node_key: GraphNodeKey, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A blocked-by-dependency outcome must carry a non-empty error message")
        return cls(
            node_key=node_key, stage=stage, status=JobExecutionStatus.BLOCKED_BY_DEPENDENCY, error_message=error_message
        )


def _validate_outcome_invariants(outcome: StageJobOutcome) -> None:
    status = outcome.status
    has_outputs = bool(outcome.produced_outputs)
    has_message = outcome.error_message is not None and outcome.error_message != ""

    if status is JobExecutionStatus.SUCCESS:
        if not has_outputs:
            raise ValueError(f"{status.value} outcome requires produced outputs")
        if has_message:
            raise ValueError(f"{status.value} outcome must not carry an error message")

    if status in (JobExecutionStatus.FAILED, JobExecutionStatus.INFEASIBLE, JobExecutionStatus.BLOCKED_BY_DEPENDENCY):
        if not has_message:
            raise ValueError(f"{status.value} outcome requires a non-empty error message")
        if has_outputs:
            raise ValueError(f"{status.value} outcome must not carry produced outputs")
