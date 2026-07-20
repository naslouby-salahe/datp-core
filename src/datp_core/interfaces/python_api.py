"""Public Python use-case entry points."""

from __future__ import annotations

from pathlib import Path

from ..composition.bootstrap import bootstrap
from ..kernel.ids import ExperimentId
from ..orchestration.planning import build_execution_plan, plan_experiment


def describe_catalogue(root: Path) -> tuple[int, int, int]:
    catalogue = bootstrap(root).configuration.study
    return len(catalogue.datasets), len(catalogue.populations), len(catalogue.experiments)


def explain_experiment_plan(root: Path, experiment_id: str) -> int:
    application = bootstrap(root)
    return len(build_execution_plan(plan_experiment(application.configuration, ExperimentId(experiment_id))).jobs)
