"""Plan expansion and calibration/test artifact-isolation tests."""

from datp_core.composition.root import build_application
from datp_core.domain.artifacts import ArtifactKind
from datp_core.domain.identifiers import ExperimentId


def test_complete_catalogue_resolves_and_anchor_plan_separates_scores() -> None:
    app = build_application()
    assert (len(app.config.populations), len(app.config.experiments)) == (7, 23)
    plan = app.plan_experiment.execute(ExperimentId("anchor_reproduction"))
    assert plan.node_count > 0
    plan.validate_acyclic()
    for job in plan.jobs:
        if job.stage.value == "threshold_construction":
            assert all(item.kind is not ArtifactKind.TEST_SCORES for item in job.inputs)
        if job.stage.value == "operating_point_evaluation":
            assert all(item.kind is not ArtifactKind.CALIBRATION_SCORES for item in job.inputs)
