"""Identity builder determinism and collision tests."""

from datp_core.app import build_application
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import expand_experiment_jobs


def test_identity_builder_determinism_across_all_experiments() -> None:
    """Every experiment plan built twice must produce identical node keys."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan_a = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        plan_b = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        jobs_a = {j.node_key.label: (j.output.node_key.label, j.stage.value) for j in plan_a.jobs}
        jobs_b = {j.node_key.label: (j.output.node_key.label, j.stage.value) for j in plan_b.jobs}
        assert jobs_a == jobs_b, f"Experiment {exp_id.value} produced different plans across two builds"


def test_no_duplicate_node_keys_in_any_experiment() -> None:
    """No experiment plan may contain duplicate node keys."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        seen: set[str] = set()
        for job in plan.jobs:
            assert job.node_key.label not in seen, (
                f"Duplicate node key '{job.node_key.label}' in experiment '{exp_id.value}'"
            )
            seen.add(job.node_key.label)


def test_no_duplicate_output_keys_in_any_experiment() -> None:
    """No experiment plan may produce duplicate output node keys."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        seen: set[str] = set()
        for job in plan.jobs:
            assert job.output.node_key.label not in seen, (
                f"Duplicate output key '{job.output.node_key.label}' in experiment '{exp_id.value}'"
            )
            seen.add(job.output.node_key.label)


def test_identity_builder_purity() -> None:
    """IdentityBuilder methods are stateless — repeated calls produce identical results."""
    from datp_core.pipeline.stages.context import StageJobContext

    ctx = StageJobContext(experiment_id=ExperimentId("test_exp"), seed=42)
    builder = IdentityBuilder()
    id1 = builder.preflight_node_key(ctx)
    id2 = builder.preflight_node_key(ctx)
    assert id1 == id2
    assert id1.label == "test_exp:preflight"

    eval_ctx = StageJobContext(experiment_id=ExperimentId("test_exp"), seed=42, evaluation_label="my_eval")
    aid1 = builder.threshold_node_key(eval_ctx)
    aid2 = builder.threshold_node_key(eval_ctx)
    assert aid1 == aid2
    assert aid1.label == "test_exp:threshold_construction:seed_42:my_eval"


def test_typed_context_correctness_for_every_job_stage() -> None:
    """Every planned job's context maps to the correct stage-required fields."""
    from datp_core.pipeline.stages.enums import StageKind

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
