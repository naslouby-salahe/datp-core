"""Stage execution never runs work whose prerequisite did not materialize."""

from datp_core.app import build_application
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.execution import ExecuteExperimentUseCase
from datp_core.experiments.planning.builder import ExperimentPlanBuilder
from datp_core.experiments.planning.paths import ExperimentPaths
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind


def test_execution_suppresses_jobs_after_an_unavailable_prerequisite() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    plan_builder = ExperimentPlanBuilder(paths=paths)
    report = ExecuteExperimentUseCase(app.config, plan_builder, handlers=()).execute(
        ExperimentId("anchor_reproduction")
    )
    preflight = next(outcome for outcome in report.outcomes if outcome.stage is StageKind.PREFLIGHT)
    materialization = next(outcome for outcome in report.outcomes if outcome.stage is StageKind.DATASET_MATERIALIZATION)
    assert preflight.status is JobExecutionStatus.FAILED
    assert preflight.error_message == "No stage handler is registered"
    assert materialization.status is JobExecutionStatus.BLOCKED_BY_DEPENDENCY
    assert materialization.error_message is not None
    assert "Unavailable prerequisite jobs" in materialization.error_message
