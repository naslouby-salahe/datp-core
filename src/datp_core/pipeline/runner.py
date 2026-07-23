"""Generic DAG-execution primitive: walk a validated PlanningGraph in topological order,
dispatching each job to its registered stage handler and propagating dependency failure.

Owns only "how a DAG of stage jobs gets walked" -- it has no knowledge of experiments,
datasets, or any other feature concept. What to run is decided by experiments/execution.py.
"""

from __future__ import annotations

from collections.abc import Mapping

from datp_core.pipeline.identifiers import JobId, RunId
from datp_core.pipeline.models import JobExecutionStatus, PlanningGraph, StageJobOutcome, StageKind
from datp_core.pipeline.stages import StageHandler


def _execute_or_fail(handler, job, run_id):
    """Execute a handler or return a failure outcome if no handler is registered."""
    if handler is not None:
        return handler.execute(job, run_id)
    return StageJobOutcome.failed(
        job_id=job.job_id,
        stage=job.stage,
        error_message="No stage handler is registered",
    )


def run_planning_graph(
    graph: PlanningGraph,
    handlers: Mapping[StageKind, StageHandler],
    run_id: RunId,
) -> tuple[StageJobOutcome, ...]:
    """Execute every job in the graph's topological order, skipping jobs whose dependencies failed."""
    sorted_jobs = graph.lexicographical_topological_sort()
    outcomes: list[StageJobOutcome] = []
    outcomes_by_job_id: dict[JobId, StageJobOutcome] = {}

    for job in sorted_jobs:
        unavailable_dependencies = tuple(
            dependency
            for dependency in job.dependencies
            if outcomes_by_job_id[dependency].status not in (JobExecutionStatus.SUCCESS, JobExecutionStatus.REUSED)
        )
        handler = handlers.get(job.stage)
        outcome = (
            StageJobOutcome.skipped(
                job_id=job.job_id,
                stage=job.stage,
                error_message=(
                    "Unavailable prerequisite jobs: "
                    + ", ".join(dependency.value for dependency in unavailable_dependencies)
                ),
            )
            if unavailable_dependencies
            else _execute_or_fail(handler, job, run_id)
        )
        outcomes.append(outcome)
        outcomes_by_job_id[job.job_id] = outcome

    return tuple(outcomes)
