"""``resolve_experiment_run_id`` is the single authoritative way to resolve any experiment's run
id, including a cross-experiment reference. A run id reconstructed from only the experiment id and
execution fingerprint (omitting the source-inventory fingerprint) names a different, nonexistent
namespace than the one an experiment actually executes under -- these tests guard the remediation
fix in `experiments/identity/run_locator.py` and `experiments/identity/builder.py`."""

from __future__ import annotations

import inspect

import pytest

from datp_core.app import build_application
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.identity.builder import execution_run_id
from datp_core.experiments.identity.run_locator import resolve_experiment_run_id


def test_source_provenance_fingerprint_is_a_required_argument() -> None:
    """Regression guard: the 2-argument incomplete-construction footgun must be structurally
    impossible, not merely discouraged by convention."""
    parameters = inspect.signature(execution_run_id).parameters
    assert parameters["source_provenance_fingerprint"].default is inspect.Parameter.empty


def test_resolve_experiment_run_id_matches_actual_execution_namespace() -> None:
    """The run id resolved for a cross-experiment reference must be identical to the run id the
    referenced experiment actually executes under (computed by `ExecuteExperimentUseCase`), not a
    different string missing the source-fingerprint suffix."""
    app = build_application()
    experiment_id = ExperimentId("anchor_reproduction")
    experiment = app.config.experiments.get(experiment_id)

    from datp_core.core.identifiers import DatasetId
    from datp_core.data.sources.inventory import compute_experiment_source_fingerprint

    dataset_ids = tuple(
        DatasetId(app.config.populations.get(population_id).dataset_id.value)
        for population_id in experiment.population_ids
    )
    expected_source_fingerprint = compute_experiment_source_fingerprint(
        datasets=app.config.datasets, dataset_ids=dataset_ids
    )
    expected_run_id = execution_run_id(
        experiment_id, app.config.execution_fingerprint.value, expected_source_fingerprint
    )

    assert resolve_experiment_run_id(app.config, experiment_id) == expected_run_id


def test_resolve_experiment_run_id_is_stable_across_calls() -> None:
    app = build_application()
    experiment_id = ExperimentId("anchor_reproduction")
    first = resolve_experiment_run_id(app.config, experiment_id)
    second = resolve_experiment_run_id(app.config, experiment_id)
    assert first == second


def test_resolve_experiment_run_id_differs_across_experiments_with_different_sources() -> None:
    app = build_application()
    anchor_run = resolve_experiment_run_id(app.config, ExperimentId("anchor_reproduction"))
    confirmatory_run = resolve_experiment_run_id(
        app.config, ExperimentId("confirmatory_threshold_scope_effect")
    )
    assert anchor_run != confirmatory_run


def test_execution_run_id_cannot_be_called_without_source_fingerprint() -> None:
    with pytest.raises(TypeError):
        execution_run_id(ExperimentId("anchor_reproduction"), "some_execution_fingerprint")  # type: ignore[call-arg]
