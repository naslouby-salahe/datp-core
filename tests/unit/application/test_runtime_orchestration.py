from dataclasses import replace

import pytest

from datp_core.application.planning.plan import ScientificStageGateDecision
from datp_core.application.planning.reuse import ReuseArtifactDecision
from datp_core.application.runtime.executor import ExecuteFinalPlanRequest, PlanExecutor, StageRunner
from datp_core.application.runtime.lifecycle import StageLifecycle
from datp_core.application.runtime.preflight import (
    ArtifactCatalogueEntry,
    ArtifactCatalogueSnapshot,
    ExecutionPreflight,
    FinalPlannedStage,
)
from datp_core.application.runtime.resource_pressure import CooperativePressureOrchestrator
from datp_core.domain.errors import (
    CudaOutOfMemoryError,
    DiskSpaceError,
    DomainValidationError,
    RamPreflightError,
    UnsafeParallelismError,
)
from datp_core.domain.experiments.feasibility import BlockingReason, ScientificReadinessResult
from datp_core.domain.runtime.admissibility import BatchSize, WorkerCount
from datp_core.domain.runtime.policies import (
    PauseDecision,
    PipelineStage,
    ResourcePressureLevel,
    ResourcePressureSnapshot,
    RunStatus,
)
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry
from tests.support.runtime_orchestration import (
    runtime_fingerprint as _fingerprint,
)
from tests.support.runtime_orchestration import (
    runtime_preflight_request as _preflight_request,
)
from tests.support.runtime_orchestration import (
    runtime_profile as _profile,
)
from tests.support.score_artifacts import calibration_scores_and_eligible_clients


class _FailingRunner(StageRunner):
    def __init__(self) -> None:
        self.called = False

    def run(self, stage: FinalPlannedStage) -> None:
        del stage
        self.called = True
        raise CudaOutOfMemoryError(detail="simulated", batch="8", vram="1")


def _registry(runner: StageRunner) -> EnumMap[PipelineStage, StageRunner]:
    return EnumMap(
        entries=tuple(EnumMapEntry(key=stage, value=runner) for stage in PipelineStage),
        allowed_keys=tuple(PipelineStage),
        is_sparse=False,
    )


def test_reuse_is_finalized_before_a_runner_can_start() -> None:
    calibration_scores, _ = calibration_scores_and_eligible_clients()
    request = _preflight_request()
    result = ExecutionPreflight().validate(
        replace(
            request,
            artifact_catalogue=ArtifactCatalogueSnapshot(
                entries=(
                    ArtifactCatalogueEntry(
                        stage_fingerprint=request.draft.stages[0].stage_fingerprint,
                        reuse_decision=ReuseArtifactDecision(artifact=calibration_scores),
                    ),
                )
            ),
        )
    )
    runner = _FailingRunner()

    summary = PlanExecutor(runners=_registry(runner)).execute(ExecuteFinalPlanRequest(plan=result.final_plan))

    assert not runner.called
    assert summary.reused == (_fingerprint("a"),)
    assert summary.failed == ()


def test_cuda_oom_is_terminal_for_the_current_execution_attempt() -> None:
    result = ExecutionPreflight().validate(_preflight_request())
    runner = _FailingRunner()

    summary = PlanExecutor(runners=_registry(runner)).execute(ExecuteFinalPlanRequest(plan=result.final_plan))

    assert runner.called
    assert summary.failed == (_fingerprint("a"),)
    assert len(summary.failures) == 1
    assert type(summary.failures[0].error) is CudaOutOfMemoryError
    failed = StageLifecycle(status=RunStatus.RUNNING).fail(
        CudaOutOfMemoryError(detail="simulated", batch="8", vram="1")
    )

    assert failed.status is RunStatus.FAILED
    with pytest.raises(DomainValidationError):
        failed.transition(RunStatus.RECOVERED)
    with pytest.raises(DomainValidationError):
        failed.recover_transient_failure()


def test_pressure_rejects_a_profile_change_before_execution() -> None:
    profile = _profile()
    changed = replace(profile, scoring=replace(profile.scoring, test_batch_size=BatchSize(value=4)))
    snapshot = ResourcePressureSnapshot(
        level=ResourcePressureLevel.CRITICAL,
        ram_usage_fraction=1.0,
        vram_usage_fraction=1.0,
        load_usage_fraction=1.0,
        recommended_action=PauseDecision.PAUSE_AT_SAFE_BOUNDARY,
    )
    orchestrator = CooperativePressureOrchestrator()

    with pytest.raises(DomainValidationError, match="cannot alter"):
        orchestrator.respond(
            snapshot=snapshot,
            frozen_batch_profile=profile,
            proposed_batch_profile=changed,
        )


def test_pressure_pause_and_resume_retains_the_exact_preflight_profile() -> None:
    profile = _profile()
    snapshot = ResourcePressureSnapshot(
        level=ResourcePressureLevel.CRITICAL,
        ram_usage_fraction=1.0,
        vram_usage_fraction=1.0,
        load_usage_fraction=1.0,
        recommended_action=PauseDecision.PAUSE_AT_SAFE_BOUNDARY,
    )
    orchestrator = CooperativePressureOrchestrator()

    response = orchestrator.respond(
        snapshot=snapshot,
        frozen_batch_profile=profile,
        proposed_batch_profile=profile,
    )

    assert orchestrator.resume(response=response, frozen_batch_profile=profile) is profile


def test_preflight_preserves_the_exact_profile_and_fails_before_execution_for_insufficient_ram() -> None:
    request = _preflight_request()

    result = ExecutionPreflight().validate(request)
    invalid_request = replace(request, hardware=replace(request.hardware, ram_bytes=0))
    preflight = ExecutionPreflight()

    assert result.final_plan.resolved_batch_profile is request.resolved_batch_profile
    with pytest.raises(RamPreflightError):
        preflight.validate(invalid_request)


def test_preflight_raises_typed_disk_and_parallelism_failures_before_execution() -> None:
    request = _preflight_request()
    unwritable_resources = replace(
        request.resources,
        storage=(replace(request.resources.storage[0], writable=False),),
    )
    unsafe_resources = replace(
        request.resources,
        parallelism=replace(request.resources.parallelism, maximum_cpu_workers=WorkerCount(value=2)),
    )
    preflight = ExecutionPreflight()
    unwritable_request = replace(request, resources=unwritable_resources)
    unsafe_request = replace(request, resources=unsafe_resources)

    with pytest.raises(DiskSpaceError):
        preflight.validate(unwritable_request)
    with pytest.raises(UnsafeParallelismError):
        preflight.validate(unsafe_request)


def test_executor_rejects_a_sparse_stage_dispatch_registry_at_construction() -> None:
    runner = _FailingRunner()
    sparse_registry = EnumMap(
        entries=tuple(EnumMapEntry(key=stage, value=runner) for stage in PipelineStage),
        allowed_keys=tuple(PipelineStage),
        is_sparse=True,
    )

    with pytest.raises(DomainValidationError, match="ordered and exhaustive"):
        PlanExecutor(runners=sparse_registry)


def test_preflight_blocks_a_stage_with_failed_scientific_readiness() -> None:
    request = _preflight_request()
    blocked_stage = replace(
        request.draft.stages[0],
        scientific_gate_decision=ScientificStageGateDecision(
            readiness=ScientificReadinessResult(blockers=(BlockingReason.FAILED_ANCHOR_GATE,))
        ),
    )

    result = ExecutionPreflight().validate(replace(request, draft=replace(request.draft, stages=(blocked_stage,))))

    assert result.final_plan.blocked_stages == (_fingerprint(),)
