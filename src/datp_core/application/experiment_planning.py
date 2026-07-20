"""Application use case for experiment planning DAG generation."""

from __future__ import annotations

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.identifiers import ExperimentId
from datp_core.planning.expansion import expand_experiment_jobs
from datp_core.planning.graph import PlanningGraph
from datp_core.planning.validation import ExecutionPlanValidator


class PlanExperimentUseCase:
    """Use case expanding an experiment into a validated planning graph."""

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config

    def execute(self, experiment_id: ExperimentId) -> PlanningGraph:
        experiment = self._config.experiments.get(experiment_id)
        graph = expand_experiment_jobs(experiment, self._config)
        validator = ExecutionPlanValidator()
        res = validator.validate(graph)
        if not res.is_valid:
            raise ValueError(f"Execution plan for '{experiment_id}' is invalid: {res.errors}")
        return graph
