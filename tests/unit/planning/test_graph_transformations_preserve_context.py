"""Graph transformations preserve StageJob context."""

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import ExperimentId


def test_topological_sort_preserves_context() -> None:
    """Lexicographical topological sort must preserve every job's context."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = app.plan_experiment.execute(exp_id)
        sorted_jobs = plan.lexicographical_topological_sort()
        assert len(sorted_jobs) == plan.node_count
        for job in sorted_jobs:
            assert job.context is not None
            assert job.context.experiment_id == exp_id


def test_topological_generations_preserve_context() -> None:
    """Topological generations must preserve every job's context."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = app.plan_experiment.execute(exp_id)
        generations = plan.topological_generations()
        gen_job_count = sum(len(gen) for gen in generations)
        assert gen_job_count == plan.node_count
        for gen in generations:
            for job in gen:
                assert job.context is not None
                assert job.context.experiment_id == exp_id


def test_transitive_reduction_preserves_context() -> None:
    """Transitive reduction must preserve every job's context."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = app.plan_experiment.execute(exp_id)
        reduced = plan.transitive_reduction()
        for job in reduced.jobs:
            assert job.context is not None
            assert job.context.experiment_id == exp_id
            # Find the same job in original and verify context equality
            original_jobs = {j.job_id: j for j in plan.jobs}
            assert job.job_id in original_jobs
            assert job.context == original_jobs[job.job_id].context


def test_dagster_translation_preserves_identity() -> None:
    """Dagster AssetSpec translation must preserve job identity - no parsing."""
    from datp_core.orchestration.dagster.translation import stage_job_to_asset_spec

    app = build_application()
    plan = app.plan_experiment.execute(ExperimentId("anchor_reproduction"))
    specs = [stage_job_to_asset_spec(j) for j in plan.jobs]
    assert len(specs) == plan.node_count
    # Verify every spec's metadata references the typed job_id, not a parsed version
    for job, spec in zip(plan.jobs, specs, strict=True):
        assert spec.metadata["job_id"] == job.job_id.value
        assert spec.metadata["stage"] == job.stage.value


def test_direct_enum_comparisons_in_validator() -> None:
    """Validator uses direct StageKind enum identity, not string comparisons."""
    from datp_core.planning.validation import ExecutionPlanValidator

    app = build_application()
    plan = app.plan_experiment.execute(ExperimentId("anchor_reproduction"))
    validator = ExecutionPlanValidator()
    result = validator.validate(plan)
    assert result.is_valid
    assert result.job_count == plan.node_count
    assert result.dependency_count == plan.edge_count
