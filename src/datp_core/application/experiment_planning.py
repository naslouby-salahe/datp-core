"""Application use case for experiment planning DAG generation."""

from __future__ import annotations

from datp_core.config.resolver import resolve_catalogue
from datp_core.domain.identifiers import ExperimentId
from datp_core.planning.expansion import expand_experiment_jobs
from datp_core.planning.graph import PlanningGraph


class PlanExperimentUseCase:
    def execute(self, experiment_id: ExperimentId) -> PlanningGraph:
        catalogue = resolve_catalogue()
        experiment = catalogue.experiments.get(experiment_id)
        return expand_experiment_jobs(experiment, catalogue)
