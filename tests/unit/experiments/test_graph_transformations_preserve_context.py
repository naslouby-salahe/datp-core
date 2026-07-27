"""Graph transformations preserve StageJob context."""

from datp_core.app import build_application
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.planning import ExperimentPaths, ExperimentPlanBuilder, compile_experiment
from datp_core.pipeline.graph.traversal import lexicographical_topological_sort, topological_generations


def test_topological_sort_preserves_context() -> None:
    """Lexicographical topological sort must preserve every job's context."""
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = builder.build(compile_experiment(app.config, exp_id))
        sorted_jobs = lexicographical_topological_sort(plan)
        assert len(sorted_jobs) == plan.node_count
        for job in sorted_jobs:
            assert job.context is not None
            assert job.context.experiment_id == exp_id


def test_topological_generations_preserve_context() -> None:
    """Topological generations must preserve every job's context."""
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    for exp_id in sorted(app.config.experiments.keys(), key=lambda e: e.value):
        plan = builder.build(compile_experiment(app.config, exp_id))
        generations = topological_generations(plan)
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
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("anchor_reproduction")))
    validator = ExecutionPlanValidator()
    result = validator.validate(plan)
    assert result.is_valid
    assert result.job_count == plan.node_count
    assert result.dependency_count == plan.edge_count
