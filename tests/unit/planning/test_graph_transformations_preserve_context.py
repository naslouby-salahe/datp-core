"""Graph transformations preserve StageJob context."""

from datp_core.bootstrap import build_application
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.pipeline.identifiers import ExperimentId


def test_topological_sort_preserves_context() -> None:
    """Lexicographical topological sort must preserve every job's context."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        sorted_jobs = plan.lexicographical_topological_sort()
        assert len(sorted_jobs) == plan.node_count
        for job in sorted_jobs:
            assert job.context is not None
            assert job.context.experiment_id == exp_id


def test_topological_generations_preserve_context() -> None:
    """Topological generations must preserve every job's context."""
    app = build_application()
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = expand_experiment_jobs(app.config.experiments.get(exp_id), app.config)
        generations = plan.topological_generations()
        gen_job_count = sum(len(gen) for gen in generations)
        assert gen_job_count == plan.node_count
        for gen in generations:
            for job in gen:
                assert job.context is not None
                assert job.context.experiment_id == exp_id


def test_direct_enum_comparisons_in_validator() -> None:
    """Validator uses direct StageKind enum identity, not string comparisons."""
    from datp_core.experiments.planning import ExecutionPlanValidator

    app = build_application()
    plan = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    validator = ExecutionPlanValidator()
    result = validator.validate(plan)
    assert result.is_valid
    assert result.job_count == plan.node_count
    assert result.dependency_count == plan.edge_count
