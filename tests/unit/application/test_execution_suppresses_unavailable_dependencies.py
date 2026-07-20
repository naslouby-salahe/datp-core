"""Stage execution never runs work whose prerequisite did not materialize."""

from datp_core.application.experiment_execution import ExecuteExperimentUseCase
from datp_core.composition.root import build_application
from datp_core.domain.identifiers import ExperimentId
from datp_core.domain.outcomes import JobExecutionStatus, StageKind


def test_execution_suppresses_jobs_after_an_unavailable_prerequisite() -> None:
    config = build_application().config
    report = ExecuteExperimentUseCase(config, handlers=()).execute(ExperimentId("anchor_reproduction"))
    preflight = next(outcome for outcome in report.outcomes if outcome.stage is StageKind.PREFLIGHT)
    materialization = next(outcome for outcome in report.outcomes if outcome.stage is StageKind.DATASET_MATERIALIZATION)
    assert preflight.status is JobExecutionStatus.SKIPPED
    assert materialization.status is JobExecutionStatus.SKIPPED
    assert materialization.error_message is not None
    assert "Unavailable prerequisite jobs" in materialization.error_message
