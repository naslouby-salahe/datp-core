"""Experiment execution use case: resolve an experiment's plan, then delegate the DAG walk to
pipeline/runner.py. Owns "what to run" (experiment resolution, plan expansion/validation, run
identity); pipeline/runner.py owns "how a DAG of stage jobs gets walked."
"""

from __future__ import annotations

from attrs import define

from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.experiments.identity import execution_run_id
from datp_core.experiments.planning import expand_experiment_jobs, validate_planning_graph
from datp_core.pipeline.identifiers import ExperimentId, RunId
from datp_core.pipeline.models import JobExecutionStatus, StageJobOutcome
from datp_core.pipeline.runner import run_planning_graph
from datp_core.pipeline.stages import StageHandler


@define(frozen=True, slots=True, kw_only=True)
class ExperimentExecutionReport:
    run_id: RunId
    experiment_id: ExperimentId
    outcomes: tuple[StageJobOutcome, ...]
    successful_jobs: int
    reused_jobs: int
    failed_jobs: int


class ExecuteExperimentUseCase:
    """Use case executing real DATP pipeline stage jobs derived from an experiment plan."""

    def __init__(self, config: ResolvedProjectConfiguration, handlers: tuple[StageHandler, ...]) -> None:
        self._config = config
        self._handlers = {handler.stage: handler for handler in handlers}

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        experiment = self._config.experiments.get(experiment_id)
        graph = expand_experiment_jobs(experiment, self._config)
        validate_planning_graph(graph)

        # Run ID tied collision-safely to scientific and execution identity
        run_id = execution_run_id(experiment_id, self._config.execution_fingerprint.value)

        outcomes = run_planning_graph(graph, self._handlers, run_id)

        return ExperimentExecutionReport(
            run_id=run_id,
            experiment_id=experiment_id,
            outcomes=outcomes,
            successful_jobs=sum(outcome.status is JobExecutionStatus.SUCCESS for outcome in outcomes),
            reused_jobs=sum(outcome.status is JobExecutionStatus.REUSED for outcome in outcomes),
            failed_jobs=sum(outcome.status is JobExecutionStatus.FAILED for outcome in outcomes),
        )
