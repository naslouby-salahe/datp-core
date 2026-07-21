"""Plan expansion and calibration/test artifact-isolation tests."""

from datp_core.composition.root import build_application
from datp_core.domain.artifacts import ArtifactKind
from datp_core.domain.identifiers import ExperimentId
from datp_core.domain.outcomes import StageKind


def test_complete_catalogue_resolves_and_anchor_plan_separates_scores() -> None:
    app = build_application()
    assert (len(app.config.populations), len(app.config.experiments)) == (7, 23)
    plan = app.plan_experiment.execute(ExperimentId("anchor_reproduction"))
    assert plan.node_count > 0
    plan.validate_acyclic()
    for job in plan.jobs:
        if job.stage is StageKind.THRESHOLD_CONSTRUCTION:
            assert all(item.kind is not ArtifactKind.TEST_SCORES for item in job.inputs)
        if job.stage is StageKind.OPERATING_POINT_EVALUATION:
            assert all(item.kind is not ArtifactKind.CALIBRATION_SCORES for item in job.inputs)


def test_controlled_heterogeneity_expands_every_partition_condition_without_identity_collisions() -> None:
    app = build_application()
    plan = app.plan_experiment.execute(ExperimentId("controlled_heterogeneity_response"))
    materializations = tuple(job for job in plan.jobs if job.stage is StageKind.DATASET_MATERIALIZATION)
    evaluations = tuple(job for job in plan.jobs if job.stage is StageKind.OPERATING_POINT_EVALUATION)

    assert len(materializations) == 60
    assert len(evaluations) == 180
    assert {job.context.partition_condition for job in materializations} == {
        "dirichlet_alpha_0_1",
        "dirichlet_alpha_0_3",
        "dirichlet_alpha_0_5",
        "dirichlet_alpha_1_0",
        "dirichlet_alpha_10_0",
        "iid_reference",
    }
    assert all(job.context.partition_condition is not None for job in evaluations)
    assert len({job.job_id for job in plan.jobs}) == plan.node_count
    assert len({job.output.artifact_id for job in plan.jobs}) == plan.node_count
