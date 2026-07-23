"""Plan expansion and calibration/test artifact-isolation tests."""

from datp_core.artifacts.models import ArtifactKind
from datp_core.bootstrap import build_application
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.pipeline.identifiers import ExperimentId
from datp_core.pipeline.models import StageKind


def test_complete_catalogue_resolves_and_anchor_plan_separates_scores() -> None:
    app = build_application()
    assert (len(app.config.populations), len(app.config.experiments)) == (7, 23)
    plan = expand_experiment_jobs(app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config)
    assert plan.node_count > 0
    plan.validate_acyclic()
    for job in plan.jobs:
        if job.stage is StageKind.THRESHOLD_CONSTRUCTION:
            assert all(item.kind is not ArtifactKind.TEST_SCORES for item in job.inputs)
        if job.stage is StageKind.OPERATING_POINT_EVALUATION:
            assert all(item.kind is not ArtifactKind.CALIBRATION_SCORES for item in job.inputs)


def test_controlled_heterogeneity_expands_every_partition_condition_without_identity_collisions() -> None:
    app = build_application()
    plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("controlled_heterogeneity_response")), app.config
    )
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


def test_confirmatory_plan_freezes_one_cohort_checkpoint_before_all_scores() -> None:
    app = build_application()
    plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("confirmatory_threshold_scope_effect")), app.config
    )
    selector = next(job for job in plan.jobs if job.stage is StageKind.CHECKPOINT_SELECTION)
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)

    assert len(selector.inputs) == 10
    assert len(scores) == 20
    assert all(selector.job_id in score.dependencies for score in scores)
    assert all(selector.output in score.inputs for score in scores)


def test_quantile_sensitivity_expands_every_quantile_without_score_duplication() -> None:
    app = build_application()
    plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("threshold_quantile_sensitivity")), app.config
    )
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    thresholds = tuple(job for job in plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)
    evaluations = tuple(job for job in plan.jobs if job.stage is StageKind.OPERATING_POINT_EVALUATION)

    assert len(scores) == 20
    assert len(thresholds) == len(evaluations) == 120
    assert {job.context.threshold_quantile for job in thresholds} == {0.9, 0.95, 0.975, 0.99}
    assert len({job.job_id for job in thresholds}) == len(thresholds)


def test_shrinkage_and_fixed_k_sweeps_preserve_unswept_baselines() -> None:
    app = build_application()
    shrinkage_plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("local_global_threshold_shrinkage")), app.config
    )
    shrinkage = tuple(job for job in shrinkage_plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)
    fixed_k_plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("federated_summary_comparator")), app.config
    )
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
    plan = expand_experiment_jobs(
        build_application().config.experiments.get(ExperimentId("calibration_window_size_stability")),
        build_application().config,
    )
    subsets = tuple(job for job in plan.jobs if job.stage is StageKind.CALIBRATION_SUBSAMPLING)
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    thresholds = tuple(job for job in plan.jobs if job.stage is StageKind.THRESHOLD_CONSTRUCTION)

    assert len(scores) == 20
    assert len(subsets) == 6_000
    assert {job.context.calibration_sample_count for job in subsets} == {50, 100, 250, 500, 1000, 5000}
    assert {job.context.calibration_replicate for job in subsets} == set(range(100))
    assert all(job.inputs[0].kind is ArtifactKind.CALIBRATION_SCORES for job in subsets)
    assert len(thresholds) == 24_040
    assert sum(job.context.calibration_sample_count is None for job in thresholds) == 40
    assert len({job.job_id for job in plan.jobs}) == plan.node_count


def test_cluster_fingerprint_ablation_expands_only_threshold_and_evaluation_cells() -> None:
    plan = expand_experiment_jobs(
        build_application().config.experiments.get(ExperimentId("cluster_and_family_threshold_mechanism")),
        build_application().config,
    )
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
    assert len({job.job_id for job in plan.jobs}) == plan.node_count


def test_fedprox_plan_retains_all_mu_cells_without_rematerializing() -> None:
    app = build_application()
    plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("fedprox_aggregation_stress_test")), app.config
    )
    training = tuple(job for job in plan.jobs if job.stage is StageKind.MODEL_TRAINING)
    materializations = tuple(job for job in plan.jobs if job.stage is StageKind.DATASET_MATERIALIZATION)
    selector = next(job for job in plan.jobs if job.stage is StageKind.CHECKPOINT_SELECTION)
    statistics = next(job for job in plan.jobs if job.stage is StageKind.STATISTICAL_ANALYSIS)

    assert len(materializations) == 10
    assert len(training) == 40
    assert {job.context.federated_proximal_mu for job in training} == {0.001, 0.01, 0.1, 1.0}
    assert len(selector.inputs) == 40
    assert selector.job_id in statistics.dependencies
    assert selector.output in statistics.inputs


def test_ditto_plan_retains_every_weight_with_distinct_training_identities() -> None:
    app = build_application()
    plan = expand_experiment_jobs(
        app.config.experiments.get(ExperimentId("model_personalization_absorption_test")), app.config
    )
    training = tuple(job for job in plan.jobs if job.stage is StageKind.MODEL_TRAINING)
    selector = next(job for job in plan.jobs if job.stage is StageKind.CHECKPOINT_SELECTION)
    statistics = next(job for job in plan.jobs if job.stage is StageKind.STATISTICAL_ANALYSIS)

    assert len(training) == 40
    assert {job.context.ditto_proximal_weight for job in training} == {0.001, 0.01, 0.1, 1.0}
    assert len({job.output.artifact_id for job in training}) == len(training)
    assert len(selector.inputs) == 40
    assert selector.job_id in statistics.dependencies


def test_temporal_plan_binds_each_arm_to_its_population_and_recalibration_window() -> None:
    plan = expand_experiment_jobs(
        build_application().config.experiments.get(ExperimentId("chronological_recalibration_evaluation")),
        build_application().config,
    )
    materializations = tuple(job for job in plan.jobs if job.stage is StageKind.DATASET_MATERIALIZATION)
    scores = tuple(job for job in plan.jobs if job.stage is StageKind.SCORE_GENERATION)
    one_shot_thresholds = tuple(
        job
        for job in plan.jobs
        if job.stage is StageKind.THRESHOLD_CONSTRUCTION and job.context.recalibration_mode == "one_shot"
    )

    assert len(materializations) == 20
    assert len(scores) == 50
    assert sum(job.output.kind is ArtifactKind.FUTURE_RECALIBRATION_SCORES for job in scores) == 10
    assert {job.context.population_id for job in materializations} == {
        job.context.population_id for job in plan.jobs if job.context.recalibration_mode is not None
    }
    assert all(job.inputs[0].kind is ArtifactKind.FUTURE_RECALIBRATION_SCORES for job in one_shot_thresholds)
