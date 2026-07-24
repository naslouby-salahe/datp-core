"""Execute experiment use case."""

from __future__ import annotations

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.identity.builder import execution_run_id
from datp_core.experiments.planning.jobs import expand_experiment_jobs
from datp_core.experiments.planning.validation import validate_planning_graph
from datp_core.pipeline.execution import StageHandler, run_planning_graph
from datp_core.pipeline.models import JobExecutionStatus


class ExecuteExperimentUseCase:
    def __init__(self, config: ResolvedProjectConfiguration, handlers: tuple[StageHandler, ...]) -> None:
        self._config = config
        self._handlers = {handler.stage: handler for handler in handlers}

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        experiment = self._config.experiments.get(experiment_id)
        graph = expand_experiment_jobs(experiment, self._config)
        validate_planning_graph(graph)

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
