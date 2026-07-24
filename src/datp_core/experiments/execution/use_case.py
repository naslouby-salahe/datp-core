"""Execute experiment use case."""

from __future__ import annotations

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import DatasetId, ExperimentId
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.identity.builder import execution_run_id
from datp_core.experiments.planning.jobs import expand_experiment_jobs
from datp_core.experiments.planning.validation import validate_planning_graph
from datp_core.pipeline.execution.registry import StageHandlerRegistry
from datp_core.pipeline.execution.runner import run_planning_graph
from datp_core.pipeline.stages.enums import JobExecutionStatus
from datp_core.pipeline.stages.handlers import StageHandler


class ExecuteExperimentUseCase:
    def __init__(self, config: ResolvedProjectConfiguration, handlers: tuple[StageHandler, ...]) -> None:
        self._config = config
        self._registry = StageHandlerRegistry({handler.stage: handler for handler in handlers})

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        experiment = self._config.experiments.get(experiment_id)
        graph = expand_experiment_jobs(experiment, self._config)
        validate_planning_graph(graph)

        dataset_ids = tuple(
            DatasetId(self._config.populations.get(pop_id).dataset_id.value)
            for pop_id in experiment.population_ids
        )
        source_fingerprint = compute_experiment_source_fingerprint(
            datasets=self._config.datasets, dataset_ids=dataset_ids
        )

        run_id = execution_run_id(
            experiment_id, self._config.execution_fingerprint.value, source_fingerprint
        )

        outcomes = run_planning_graph(graph, self._registry, run_id)

        return ExperimentExecutionReport(
            run_id=run_id,
            experiment_id=experiment_id,
            outcomes=outcomes,
            successful_jobs=sum(outcome.status is JobExecutionStatus.SUCCESS for outcome in outcomes),
            reused_jobs=sum(outcome.status is JobExecutionStatus.REUSED for outcome in outcomes),
            failed_jobs=sum(outcome.status is JobExecutionStatus.FAILED for outcome in outcomes),
        )
