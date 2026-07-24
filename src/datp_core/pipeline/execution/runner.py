"""Generic DAG runner: topological walk, dependency satisfaction, outcome collection."""

from __future__ import annotations

from datp_core.core.identifiers import JobId, RunId
from datp_core.pipeline.execution.registry import MissingStageHandlerError, StageHandlerRegistry
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.traversal import lexicographical_topological_sort
from datp_core.pipeline.stages.enums import DEPENDENCY_SATISFYING_STATUSES, JobExecutionStatus
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class InvalidHandlerOutcomeError(ValueError):
    """A handler returned an outcome inconsistent with the submitted job."""


def _execute_or_fail(registry: StageHandlerRegistry, job: StageJob, run_id: RunId) -> StageJobOutcome:
    try:
        handler = registry.get(job.stage)
    except MissingStageHandlerError:
        return StageJobOutcome.failed(
            job_id=job.job_id, stage=job.stage, error_message="No stage handler is registered"
        )
    outcome = handler.execute(job, run_id)
    if outcome.job_id != job.job_id or outcome.stage != job.stage:
        raise InvalidHandlerOutcomeError(
            f"Handler for '{job.stage.value}' returned outcome for "
            f"job '{outcome.job_id.value}' stage '{outcome.stage.value}'"
        )
    if outcome.status in (JobExecutionStatus.SUCCESS, JobExecutionStatus.REUSED):
        if outcome.produced_artifact != job.output:
            raise InvalidHandlerOutcomeError(
                f"Handler for '{job.stage.value}' job '{job.job_id.value}' "
                f"produced artifact '{outcome.produced_artifact}' but declared output is '{job.output}'"
            )
    return outcome


def run_planning_graph(
    graph: PlanningGraph,
    registry: StageHandlerRegistry,
    run_id: RunId,
) -> tuple[StageJobOutcome, ...]:
    sorted_jobs = lexicographical_topological_sort(graph)
    outcomes: list[StageJobOutcome] = []
    outcomes_by_job_id: dict[JobId, StageJobOutcome] = {}

    for job in sorted_jobs:
        unavailable_dependencies = tuple(
            dependency
            for dependency in job.dependencies
            if outcomes_by_job_id[dependency].status not in DEPENDENCY_SATISFYING_STATUSES
        )
        if unavailable_dependencies:
            outcome = StageJobOutcome.blocked_by_dependency(
                job_id=job.job_id,
                stage=job.stage,
                error_message=(
                    "Unavailable prerequisite jobs: "
                    + ", ".join(dependency.value for dependency in unavailable_dependencies)
                ),
            )
        else:
            outcome = _execute_or_fail(registry, job, run_id)
        outcomes.append(outcome)
        outcomes_by_job_id[job.job_id] = outcome

    return tuple(outcomes)
