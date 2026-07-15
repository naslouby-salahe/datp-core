from dataclasses import replace

import pytest

from datp_core.application.planning.reuse import ReuseArtifactDecision
from datp_core.application.runtime.executor import ExecuteFinalPlanRequest, PlanExecutor
from datp_core.application.runtime.preflight import (
    ArtifactCatalogueEntry,
    ArtifactCatalogueSnapshot,
    ExecutionPreflight,
    FinalPlannedStage,
)
from datp_core.application.runtime.resource_pressure import CooperativePressureOrchestrator
from datp_core.domain.errors import CudaOutOfMemoryError
from datp_core.domain.runtime.policies import (
    PauseDecision,
    PipelineStage,
    ResourcePressureLevel,
    ResourcePressureSnapshot,
)
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry
from tests.support.runtime_orchestration import runtime_fingerprint, runtime_preflight_request
from tests.support.score_artifacts import calibration_scores_and_eligible_clients


class _RecordingRunner:
    def __init__(self, *, fails_with_oom: bool) -> None:
        self.calls = 0
        self._fails_with_oom = fails_with_oom

    def run(self, stage: FinalPlannedStage) -> None:
        del stage
        self.calls += 1
        if self._fails_with_oom:
            raise CudaOutOfMemoryError(detail="synthetic OOM", batch="8", vram="1")


def _executor(runner: _RecordingRunner) -> PlanExecutor:
    stages = tuple(PipelineStage)
    return PlanExecutor(
        runners=EnumMap(
            entries=tuple(EnumMapEntry(key=stage, value=runner) for stage in stages),
            allowed_keys=stages,
            is_sparse=False,
        )
    )


@pytest.mark.integration
def test_synthetic_reuse_is_decided_before_the_executor_can_call_a_runner() -> None:
    request = runtime_preflight_request()
    score_set, _ = calibration_scores_and_eligible_clients()
    plan = (
        ExecutionPreflight()
        .validate(
            replace(
                request,
                artifact_catalogue=ArtifactCatalogueSnapshot(
                    entries=(
                        ArtifactCatalogueEntry(
                            stage_fingerprint=request.draft.stages[0].stage_fingerprint,
                            reuse_decision=ReuseArtifactDecision(artifact=score_set),
                        ),
                    )
                ),
            )
        )
        .final_plan
    )
    runner = _RecordingRunner(fails_with_oom=True)

    summary = _executor(runner).execute(ExecuteFinalPlanRequest(plan=plan))

    assert runner.calls == 0
    assert summary.reused == (runtime_fingerprint(),)


@pytest.mark.integration
def test_synthetic_oom_ends_the_current_execution_attempt() -> None:
    plan = ExecutionPreflight().validate(runtime_preflight_request()).final_plan
    runner = _RecordingRunner(fails_with_oom=True)

    summary = _executor(runner).execute(ExecuteFinalPlanRequest(plan=plan))

    assert runner.calls == 1
    assert summary.failed == (runtime_fingerprint(),)
    assert type(summary.failures[0].error) is CudaOutOfMemoryError


@pytest.mark.integration
def test_synthetic_pressure_pause_and_resume_uses_the_identical_frozen_profile() -> None:
    profile = runtime_preflight_request().resolved_batch_profile
    response = CooperativePressureOrchestrator().respond(
        snapshot=ResourcePressureSnapshot(
            level=ResourcePressureLevel.CRITICAL,
            ram_usage_fraction=1.0,
            vram_usage_fraction=1.0,
            load_usage_fraction=1.0,
            recommended_action=PauseDecision.PAUSE_AT_SAFE_BOUNDARY,
        ),
        frozen_batch_profile=profile,
        proposed_batch_profile=profile,
    )

    assert CooperativePressureOrchestrator().resume(response=response, frozen_batch_profile=profile) is profile
