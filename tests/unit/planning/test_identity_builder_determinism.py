"""Identity builder determinism and collision tests."""

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import ExperimentId
from datp_core.planning.expansion import expand_experiment_jobs
from datp_core.planning.identity import IdentityBuilder


def test_identity_builder_determinism_across_all_experiments() -> None:
    """Every experiment plan built twice must produce identical job IDs."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan_a = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        plan_b = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        jobs_a = {j.job_id.value: (j.output.artifact_id.value, j.stage.value) for j in plan_a.jobs}
        jobs_b = {j.job_id.value: (j.output.artifact_id.value, j.stage.value) for j in plan_b.jobs}
        assert jobs_a == jobs_b, f"Experiment {exp_id.value} produced different plans across two builds"


def test_no_duplicate_job_ids_in_any_experiment() -> None:
    """No experiment plan may contain duplicate JobId values."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        seen: set[str] = set()
        for job in plan.jobs:
            assert job.job_id.value not in seen, f"Duplicate JobId '{job.job_id.value}' in experiment '{exp_id.value}'"
            seen.add(job.job_id.value)


def test_no_duplicate_artifact_ids_in_any_experiment() -> None:
    """No experiment plan may produce duplicate ArtifactId values."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        seen: set[str] = set()
        for job in plan.jobs:
            assert job.output.artifact_id.value not in seen, (
                f"Duplicate ArtifactId '{job.output.artifact_id.value}' in experiment '{exp_id.value}'"
            )
            seen.add(job.output.artifact_id.value)


def test_identity_builder_purity() -> None:
    """IdentityBuilder methods are stateless — repeated calls produce identical results."""
    from datp_core.domain.outcomes import StageJobContext

    ctx = StageJobContext(experiment_id=ExperimentId("test_exp"), seed=42)
    builder = IdentityBuilder()
    id1 = builder.preflight_job_id(ctx)
    id2 = builder.preflight_job_id(ctx)
    assert id1 == id2
    assert str(id1) == "test_exp:preflight"

    eval_ctx = StageJobContext(experiment_id=ExperimentId("test_exp"), seed=42, evaluation_label="my_eval")
    aid1 = builder.threshold_artifact_id(eval_ctx)
    aid2 = builder.threshold_artifact_id(eval_ctx)
    assert aid1 == aid2
    assert str(aid1) == "test_exp:seed_42:my_eval:threshold_set"


def test_typed_context_correctness_for_every_job_stage() -> None:
    """Every planned job's context maps to the correct stage-required fields."""
    from datp_core.domain.outcomes import StageKind

    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        for job in plan.jobs:
            ctx = job.context
            assert ctx.experiment_id == exp_id

            if job.stage is StageKind.PREFLIGHT:
                assert ctx.seed is None
                assert ctx.evaluation_label is None
            elif job.stage is StageKind.DATASET_MATERIALIZATION:
                assert ctx.seed is not None
                assert ctx.evaluation_label is None
            elif job.stage is StageKind.MODEL_TRAINING:
                assert ctx.seed is not None
                assert ctx.evaluation_label is None
            elif job.stage is StageKind.CHECKPOINT_SELECTION:
                assert ctx.seed is None
                assert ctx.evaluation_label is None
            elif job.stage is StageKind.SCORE_GENERATION:
                assert ctx.seed is not None
                assert ctx.evaluation_label is None
            elif job.stage is StageKind.THRESHOLD_CONSTRUCTION:
                assert ctx.seed is not None
                assert ctx.evaluation_label is not None
            elif job.stage is StageKind.OPERATING_POINT_EVALUATION:
                assert ctx.seed is not None
                assert ctx.evaluation_label is not None
            elif job.stage is StageKind.STATISTICAL_ANALYSIS:
                assert ctx.seed is None
                assert ctx.evaluation_label is None
            elif job.stage is StageKind.REPORT_GENERATION:
                assert ctx.seed is None
                assert ctx.evaluation_label is None
