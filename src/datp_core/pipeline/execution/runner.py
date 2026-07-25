"""Generic DAG runner: topological walk, dependency satisfaction, outcome collection."""

from __future__ import annotations

from datp_core.pipeline.execution.registry import MissingStageHandlerError, StageHandlerRegistry
from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.traversal import lexicographical_topological_sort
from datp_core.pipeline.stages.enums import DEPENDENCY_SATISFYING_STATUSES, JobExecutionStatus
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class InvalidHandlerOutcomeError(ValueError):
    """A handler returned an outcome inconsistent with the submitted job."""


def _execute_or_fail(registry: StageHandlerRegistry, job: StageJob) -> StageJobOutcome:
    try:
        handler = registry.get(job.stage)
    except MissingStageHandlerError:
        return StageJobOutcome.failed(
            node_key=job.node_key, stage=job.stage, error_message="No stage handler is registered"
        )
    outcome = handler.execute(job)
    if outcome.node_key != job.node_key or outcome.stage != job.stage:
        raise InvalidHandlerOutcomeError(
            f"Handler for '{job.stage.value}' returned outcome for "
            f"job '{outcome.node_key.label}' stage '{outcome.stage.value}'"
        )
    if outcome.status is JobExecutionStatus.SUCCESS:
        if outcome.produced_outputs != job.outputs:
            raise InvalidHandlerOutcomeError(
                f"Handler for '{job.stage.value}' job '{job.node_key.label}' "
                "produced outputs that differ from its declared outputs"
            )
    return outcome


def run_planning_graph(
    graph: PlanningGraph,
    registry: StageHandlerRegistry,
) -> tuple[StageJobOutcome, ...]:
    sorted_jobs = lexicographical_topological_sort(graph)
    outcomes: list[StageJobOutcome] = []
    outcomes_by_key: dict[GraphNodeKey, StageJobOutcome] = {}

    for job in sorted_jobs:
        unavailable_dependencies = tuple(
            dependency
            for dependency in job.dependencies
            if outcomes_by_key[dependency].status not in DEPENDENCY_SATISFYING_STATUSES
        )
        if unavailable_dependencies:
            outcome = StageJobOutcome.blocked_by_dependency(
                node_key=job.node_key,
                stage=job.stage,
                error_message=(
                    "Unavailable prerequisite jobs: "
                    + ", ".join(dependency.label for dependency in unavailable_dependencies)
                ),
            )
        else:
            outcome = _execute_or_fail(registry, job)
        outcomes.append(outcome)
        outcomes_by_key[job.node_key] = outcome

    return tuple(outcomes)
