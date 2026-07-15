from dataclasses import dataclass
from typing import Protocol, assert_never

from datp_core.application.planning.reuse import (
    BlockedReuseDecision,
    RecomputeArtifactDecision,
    ReuseArtifactDecision,
)
from datp_core.application.runtime.lifecycle import StageLifecycle
from datp_core.application.runtime.preflight import FinalExecutionPlan, FinalPlannedStage
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DatpCoreError, DomainValidationError
from datp_core.domain.runtime.policies import PipelineStage, RunStatus
from datp_core.domain.runtime.seeds import EnumMap


class StageRunner(Protocol):
    def run(self, stage: FinalPlannedStage) -> None: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecuteFinalPlanRequest:
    plan: FinalExecutionPlan


@dataclass(frozen=True, slots=True, kw_only=True)
class StageExecutionFailure:
    stage_fingerprint: StageFingerprint
    error: DatpCoreError


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSummary:
    completed: tuple[StageFingerprint, ...]
    reused: tuple[StageFingerprint, ...]
    failed: tuple[StageFingerprint, ...]
    blocked: tuple[StageFingerprint, ...]
    failures: tuple[StageExecutionFailure, ...]


class PlanExecutor:
    def __init__(self, *, runners: EnumMap[PipelineStage, StageRunner]) -> None:
        _validate_runner_registry(runners)
        self._runners = runners

    def execute(self, request: ExecuteFinalPlanRequest) -> ExecutionSummary:
        completed: list[StageFingerprint] = []
        reused: list[StageFingerprint] = []
        failed: list[StageFingerprint] = []
        blocked: list[StageFingerprint] = []
        failures: list[StageExecutionFailure] = []
        for stage in request.plan.stages:
            lifecycle = StageLifecycle().transition(RunStatus.READY)
            match stage.reuse_decision:
                case ReuseArtifactDecision():
                    lifecycle = lifecycle.transition(RunStatus.REUSED).transition(RunStatus.COMPLETED)
                    reused.append(stage.stage_fingerprint)
                    completed.append(stage.stage_fingerprint)
                case BlockedReuseDecision():
                    lifecycle = lifecycle.transition(RunStatus.BLOCKED)
                    blocked.append(stage.stage_fingerprint)
                case RecomputeArtifactDecision():
                    lifecycle = lifecycle.transition(RunStatus.RUNNING)
                    try:
                        self._runner_for(stage.stage).run(stage)
                    except DatpCoreError as error:
                        lifecycle = lifecycle.fail(error)
                        failed.append(stage.stage_fingerprint)
                        failures.append(StageExecutionFailure(stage_fingerprint=stage.stage_fingerprint, error=error))
                    else:
                        lifecycle = lifecycle.transition(RunStatus.COMPLETED)
                        completed.append(stage.stage_fingerprint)
                case _ as unreachable:
                    assert_never(unreachable)
            if lifecycle.status not in {RunStatus.COMPLETED, RunStatus.BLOCKED, RunStatus.FAILED}:
                raise DomainValidationError(
                    detail="executor must leave every stage in a terminal lifecycle state",
                    value=lifecycle.status.value,
                    constraint="completed, blocked, or failed",
                )
        return ExecutionSummary(
            completed=tuple(completed),
            reused=tuple(reused),
            failed=tuple(failed),
            blocked=tuple(blocked),
            failures=tuple(failures),
        )

    def _runner_for(self, stage: PipelineStage) -> StageRunner:
        match stage:
            case PipelineStage.SOURCE_INSPECTION:
                return self._registered_runner(PipelineStage.SOURCE_INSPECTION)
            case PipelineStage.FEASIBILITY_AUDIT:
                return self._registered_runner(PipelineStage.FEASIBILITY_AUDIT)
            case PipelineStage.PARTITION:
                return self._registered_runner(PipelineStage.PARTITION)
            case PipelineStage.SPLIT_BUILD:
                return self._registered_runner(PipelineStage.SPLIT_BUILD)
            case PipelineStage.PREPROCESSOR_FIT:
                return self._registered_runner(PipelineStage.PREPROCESSOR_FIT)
            case PipelineStage.SPLIT_MATERIALIZE:
                return self._registered_runner(PipelineStage.SPLIT_MATERIALIZE)
            case PipelineStage.TRAIN:
                return self._registered_runner(PipelineStage.TRAIN)
            case PipelineStage.CHECKPOINT_SELECT:
                return self._registered_runner(PipelineStage.CHECKPOINT_SELECT)
            case PipelineStage.CALIBRATION_SCORE:
                return self._registered_runner(PipelineStage.CALIBRATION_SCORE)
            case PipelineStage.TEST_SCORE:
                return self._registered_runner(PipelineStage.TEST_SCORE)
            case PipelineStage.TEMPORAL_SCORE:
                return self._registered_runner(PipelineStage.TEMPORAL_SCORE)
            case PipelineStage.THRESHOLD:
                return self._registered_runner(PipelineStage.THRESHOLD)
            case PipelineStage.EVALUATE:
                return self._registered_runner(PipelineStage.EVALUATE)
            case PipelineStage.ANALYZE:
                return self._registered_runner(PipelineStage.ANALYZE)
            case PipelineStage.RESOURCE_COST:
                return self._registered_runner(PipelineStage.RESOURCE_COST)
            case PipelineStage.RESULT_FREEZE:
                return self._registered_runner(PipelineStage.RESULT_FREEZE)
            case PipelineStage.REPORT:
                return self._registered_runner(PipelineStage.REPORT)
            case _:
                assert_never(stage)

    def _registered_runner(self, stage: PipelineStage) -> StageRunner:
        for entry in self._runners.entries:
            if entry.key is stage:
                return entry.value
        raise DomainValidationError(
            detail="stage runner registry is incomplete",
            value=stage.value,
            constraint="exhaustive PipelineStage registry",
        )


def _validate_runner_registry(runners: EnumMap[PipelineStage, StageRunner]) -> None:
    entry_keys = tuple(entry.key for entry in runners.entries)
    expected_keys = tuple(PipelineStage)
    if not _has_exhaustive_ordered_runners(runners=runners, entry_keys=entry_keys, expected_keys=expected_keys):
        raise DomainValidationError(
            detail="stage runner registry must be ordered and exhaustive at executor construction",
            value=repr(entry_keys),
            constraint="one StageRunner for every PipelineStage in declared order",
        )


def _has_exhaustive_ordered_runners(
    *,
    runners: EnumMap[PipelineStage, StageRunner],
    entry_keys: tuple[PipelineStage, ...],
    expected_keys: tuple[PipelineStage, ...],
) -> bool:
    return all((not runners.is_sparse, runners.allowed_keys == expected_keys, entry_keys == expected_keys))
