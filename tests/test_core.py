"""Core system integration and composition tests."""

from __future__ import annotations

from pathlib import Path

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import ClientId, ExperimentId, ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores
from datp_core.domain.values import Probability

ROOT = Path(__file__).parents[1]


def test_complete_catalogue_resolves_and_every_experiment_plans() -> None:
    app = build_application()
    catalogue = app.describe_catalogue.execute()
    counts = (
        len(catalogue.populations),
        len(catalogue.experiments),
    )
    assert counts == (7, 23)

    # Plan anchor reproduction
    planning_graph = app.plan_experiment.execute(ExperimentId("anchor_reproduction"))
    assert planning_graph.node_count > 0
    planning_graph.validate_acyclic()


def test_configuration_validation_passes() -> None:
    app = build_application()
    assert app.validate_configuration.execute() is True


def test_threshold_estimator_accepts_benign_calibration_references() -> None:
    app = build_application()
    calibration = (
        BenignCalibrationScores(client_id=ClientId("c1"), values=(0.1, 0.2, 0.3)),
        BenignCalibrationScores(client_id=ClientId("c2"), values=(0.3, 0.4, 0.5)),
    )
    t_set = app.construct_thresholds.execute(
        ThresholdPolicyId("local_global_shrinkage_p95"),
        calibration,
        Probability(0.95),
        shrinkage_weight=0.5,
    )
    assert len(t_set.values) == 2
    assert all(val.effective_lambda == 0.5 for val in t_set.values)
