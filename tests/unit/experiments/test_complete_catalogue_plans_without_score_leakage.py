"""Plan expansion and calibration/test artifact-isolation tests."""

from datp_core.app import build_application
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments import RecalibrationMode
from datp_core.experiments.planning import ExperimentPaths, ExperimentPlanBuilder, compile_experiment
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.enums import StageKind


def test_complete_catalogue_resolves_and_anchor_plan_separates_scores() -> None:
    app = build_application()
    assert (len(app.config.populations), len(app.config.experiments)) == (7, 23)
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("anchor_reproduction")))
    assert plan.node_count > 0
    validate_acyclic(plan)
    for job in plan.jobs:
        if job.stage is StageKind.THRESHOLD_CONSTRUCTION:
            assert all(item.name != "test_scores" for item in job.inputs)
        if job.stage is StageKind.OPERATING_POINT_EVALUATION:
            assert all("calibration" not in item.name for item in job.inputs)


def test_controlled_heterogeneity_expands_every_partition_condition_without_identity_collisions() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("controlled_heterogeneity_response")))
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
    assert len({job.node_key for job in plan.jobs}) == plan.node_count
    assert len({path.relative_path for job in plan.jobs for path in job.outputs}) == sum(
        len(job.outputs) for job in plan.jobs
    )


def test_confirmatory_plan_freezes_one_cohort_checkpoint_before_all_scores() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("confirmatory_threshold_scope_effect")))
    selector = next(job for job in plan.jobs if job.stage is StageKind.CHECKPOINT_SELECTION)
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)

    assert len(selector.inputs) == 20
    assert len(scores) == 20
    assert all(selector.node_key in score.dependencies for score in scores)
    assert all(
        any(item.name == "checkpoint_selection" and item.producer == selector.node_key for item in score.inputs)
        for score in scores
    )


def test_quantile_sensitivity_expands_every_quantile_without_score_duplication() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("threshold_quantile_sensitivity")))
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    thresholds = tuple(job for job in plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)
    evaluations = tuple(job for job in plan.jobs if job.stage is StageKind.OPERATING_POINT_EVALUATION)

    assert len(scores) == 20
    assert len(thresholds) == len(evaluations) == 120
    assert {job.context.threshold_quantile for job in thresholds} == {0.9, 0.95, 0.975, 0.99}
    assert len({job.node_key for job in thresholds}) == len(thresholds)


def test_shrinkage_and_fixed_k_sweeps_preserve_unswept_baselines() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    shrinkage_plan = builder.build(compile_experiment(app.config, ExperimentId("local_global_threshold_shrinkage")))
    shrinkage = tuple(job for job in shrinkage_plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)
    fixed_k_plan = builder.build(compile_experiment(app.config, ExperimentId("federated_summary_comparator")))
    fixed_k = tuple(job for job in fixed_k_plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)

    assert len(shrinkage) == 70
    assert {job.context.shrinkage_weight for job in shrinkage if job.context.shrinkage_weight is not None} == {
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    }
    assert len([job for job in shrinkage if job.context.shrinkage_weight is None]) == 20
    assert {
        job.context.federated_summary_fixed_k for job in fixed_k if job.context.federated_summary_fixed_k is not None
    } == {
        2.0,
        2.5,
        3.0,
    }
    assert len([job for job in fixed_k if job.context.federated_summary_fixed_k is None]) == 50


def test_calibration_window_sweep_reuses_scores_and_expands_nested_replicates() -> None:
    config = build_application().config
    paths = ExperimentPaths(
        outputs_root=config.paths.outputs,
        repository_root=config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(config, ExperimentId("calibration_window_size_stability")))
    subsets = tuple(job for job in plan.jobs if job.stage is StageKind.CALIBRATION_SUBSAMPLING)
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    thresholds = tuple(job for job in plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)

    assert len(scores) == 20
    assert len(subsets) == 6_000
    assert {job.context.calibration_sample_count for job in subsets} == {50, 100, 250, 500, 1000, 5000}
    assert {job.context.calibration_replicate for job in subsets} == set(range(100))
    assert all(job.inputs[0].name == "calibration_scores" for job in subsets)
    assert len(thresholds) == 24_040
    assert sum(job.context.calibration_sample_count is None for job in thresholds) == 40
    assert len({job.node_key for job in plan.jobs}) == plan.node_count


def test_cluster_fingerprint_ablation_expands_only_threshold_and_evaluation_cells() -> None:
    config = build_application().config
    paths = ExperimentPaths(
        outputs_root=config.paths.outputs,
        repository_root=config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(config, ExperimentId("cluster_and_family_threshold_mechanism")))
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    ablations = tuple(
        job
        for job in plan.jobs
        if job.stage is StageKind.THRESHOLD_CONSTRUCTION and job.context.fingerprint_features is not None
    )

    assert len(scores) == 20
    assert len(ablations) == 40
    assert {job.context.fingerprint_features for job in ablations} == {
        ("mean_error",),
        ("p95_error",),
        ("mean_error", "std_error"),
        ("mean_error", "std_error", "skew_error", "p95_error"),
    }
    assert len({job.node_key for job in plan.jobs}) == plan.node_count


def test_fedprox_plan_retains_all_mu_cells_without_rematerializing() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("fedprox_aggregation_stress_test")))
    training = tuple(job for job in plan.jobs if job.stage is StageKind.MODEL_TRAINING)
    materializations = tuple(job for job in plan.jobs if job.stage is StageKind.DATASET_MATERIALIZATION)
    selector = next(job for job in plan.jobs if job.stage is StageKind.CHECKPOINT_SELECTION)
    statistics = next(job for job in plan.jobs if job.stage is StageKind.STATISTICAL_ANALYSIS)

    assert len(materializations) == 10
    assert len(training) == 40
    assert {job.context.federated_proximal_mu for job in training} == {0.001, 0.01, 0.1, 1.0}
    assert len(selector.inputs) == 80
    assert selector.node_key in statistics.dependencies
    assert any(
        item.name.endswith("checkpoint_selection") and item.producer == selector.node_key for item in statistics.inputs
    )


def test_ditto_plan_retains_every_weight_with_distinct_training_identities() -> None:
    app = build_application()
    paths = ExperimentPaths(
        outputs_root=app.config.paths.outputs,
        repository_root=app.config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(app.config, ExperimentId("model_personalization_absorption_test")))
    training = tuple(job for job in plan.jobs if job.stage is StageKind.MODEL_TRAINING)
    selector = next(job for job in plan.jobs if job.stage is StageKind.CHECKPOINT_SELECTION)
    statistics = next(job for job in plan.jobs if job.stage is StageKind.STATISTICAL_ANALYSIS)

    assert len(training) == 40
    assert {job.context.ditto_proximal_weight for job in training} == {0.001, 0.01, 0.1, 1.0}
    assert len({job.output_path("checkpoint") for job in training}) == len(training)
    assert len(selector.inputs) == 80
    assert selector.node_key in statistics.dependencies


def test_temporal_plan_binds_each_arm_to_its_population_and_recalibration_window() -> None:
    config = build_application().config
    paths = ExperimentPaths(
        outputs_root=config.paths.outputs,
        repository_root=config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    plan = builder.build(compile_experiment(config, ExperimentId("chronological_recalibration_evaluation")))
    materializations = tuple(job for job in plan.jobs if job.stage is StageKind.DATASET_MATERIALIZATION)
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    one_shot_thresholds = tuple(
        job
        for job in plan.jobs
        if job.stage is StageKind.THRESHOLD_CONSTRUCTION
        and job.context.recalibration_mode is RecalibrationMode.ONE_SHOT
    )

    assert len(materializations) == 20
    assert len(scores) == 50
    assert sum(any(item.name == "future_recalibration_scores" for item in job.outputs) for job in scores) == 10
    assert {job.context.population_id for job in materializations} == {
        job.context.population_id
        for job in plan.jobs
        if hasattr(job.context, "recalibration_mode") and job.context.recalibration_mode is not None
    }
    assert all(job.inputs[0].name == "future_recalibration_scores" for job in one_shot_thresholds)


def test_campaign_plan_deduplicates_equivalent_upstream_producers() -> None:
    config = build_application().config
    paths = ExperimentPaths(
        outputs_root=config.paths.outputs,
        repository_root=config.paths.repository_root,
    )
    builder = ExperimentPlanBuilder(paths=paths)
    experiment_ids = (
        ExperimentId("anchor_reproduction"),
        ExperimentId("confirmatory_threshold_scope_effect"),
        ExperimentId("shared_threshold_construction_sensitivity"),
    )
    compiled_experiments = tuple(compile_experiment(config, eid) for eid in experiment_ids)
    plan = builder.build_campaign(compiled_experiments)
    shared_producers = tuple(job for job in plan.jobs if job.node_key.label.startswith("shared:"))

    assert shared_producers
    assert all(output.relative_path.startswith("shared/") for job in shared_producers for output in job.outputs)
    assert all(
        any(input_.producer == producer.node_key for consumer in plan.jobs for input_ in consumer.inputs)
        for producer in shared_producers
    )
