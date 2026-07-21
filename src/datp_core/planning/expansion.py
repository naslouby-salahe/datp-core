"""Demand-driven stage job derivation and seed expansion logic."""

from __future__ import annotations

from itertools import product

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.catalogue import ConditionSweepRecord, ExperimentRecord
from datp_core.domain.outcomes import StageJob, StageJobContext, StageKind
from datp_core.planning.graph import PlanningGraph
from datp_core.planning.identity import IdentityBuilder


def expand_experiment_jobs(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> PlanningGraph:
    """Expand resolved experiment into a complete, validated execution plan graph."""
    seed_cohort = config.seed_cohorts.get(experiment.seed_cohort_id)
    builder = IdentityBuilder()
    jobs: list[StageJob] = []

    experiment_ctx = StageJobContext(experiment_id=experiment.identifier)

    # 1. Preflight check job
    pf_job_id, pf_output = builder.preflight_job(experiment_ctx)
    preflight_job = StageJob(
        job_id=pf_job_id,
        stage=StageKind.PREFLIGHT,
        context=experiment_ctx,
        inputs=(),
        output=pf_output,
        dependencies=(),
    )
    jobs.append(preflight_job)

    eval_job_outputs: list = []
    eval_job_ids: list = []
    conditions = tuple(
        condition.name
        for sweep in experiment.sweeps
        if isinstance(sweep, ConditionSweepRecord)
        for condition in sweep.conditions
    ) or (None,)

    # 2. Derive jobs per seed
    for seed, condition in product(seed_cohort.training_seeds, conditions):
        seed_ctx = StageJobContext(
            experiment_id=experiment.identifier,
            seed=int(seed.value),
            partition_condition=condition,
        )

        # Dataset materialization
        mat_ids = builder.materialization_job(seed_ctx, pf_output, pf_job_id)
        mat_job = StageJob(
            job_id=mat_ids[0],
            stage=StageKind.DATASET_MATERIALIZATION,
            context=seed_ctx,
            inputs=mat_ids[2],
            output=mat_ids[1],
            dependencies=mat_ids[3],
        )
        jobs.append(mat_job)

        # Model Training
        train_ids = builder.training_job(seed_ctx, mat_ids[1], mat_ids[0])
        train_job = StageJob(
            job_id=train_ids[0],
            stage=StageKind.MODEL_TRAINING,
            context=seed_ctx,
            inputs=train_ids[2],
            output=train_ids[1],
            dependencies=train_ids[3],
        )
        jobs.append(train_job)

        # Calibration Score Generation
        calib_ids = builder.calibration_score_job(seed_ctx, train_ids[1], mat_ids[1], train_ids[0])
        calib_score_job = StageJob(
            job_id=calib_ids[0],
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            inputs=calib_ids[2],
            output=calib_ids[1],
            dependencies=calib_ids[3],
        )
        jobs.append(calib_score_job)

        # Test Score Generation
        test_ids = builder.test_score_job(seed_ctx, train_ids[1], mat_ids[1], train_ids[0])
        test_score_job = StageJob(
            job_id=test_ids[0],
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            inputs=test_ids[2],
            output=test_ids[1],
            dependencies=test_ids[3],
        )
        jobs.append(test_score_job)

        # Threshold Construction & Evaluation jobs per evaluation spec
        for eval_spec in experiment.evaluations:
            eval_ctx = StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                partition_condition=condition,
                evaluation_label=eval_spec.label,
                population_id=eval_spec.population_id,
                threshold_policy_id=eval_spec.threshold_policy_id,
            )

            thresh_ids = builder.threshold_job(eval_ctx, calib_ids[1], calib_ids[0])
            thresh_job = StageJob(
                job_id=thresh_ids[0],
                stage=StageKind.THRESHOLD_CONSTRUCTION,
                context=eval_ctx,
                inputs=thresh_ids[2],
                output=thresh_ids[1],
                dependencies=thresh_ids[3],
            )
            jobs.append(thresh_job)

            eval_ids = builder.evaluation_job(eval_ctx, thresh_ids[1], test_ids[1], thresh_ids[0], test_ids[0])
            eval_job = StageJob(
                job_id=eval_ids[0],
                stage=StageKind.OPERATING_POINT_EVALUATION,
                context=eval_ctx,
                inputs=eval_ids[2],
                output=eval_ids[1],
                dependencies=eval_ids[3],
            )
            jobs.append(eval_job)
            eval_job_outputs.append(eval_ids[1])
            eval_job_ids.append(eval_ids[0])

    # 3. Statistical Analysis job across all seed evaluation outputs
    stats_ids = builder.statistical_analysis_job(experiment_ctx, tuple(eval_job_outputs), tuple(eval_job_ids))
    stats_job = StageJob(
        job_id=stats_ids[0],
        stage=StageKind.STATISTICAL_ANALYSIS,
        context=experiment_ctx,
        inputs=stats_ids[2],
        output=stats_ids[1],
        dependencies=stats_ids[3],
    )
    jobs.append(stats_job)

    # 4. Report Generation job
    report_ids = builder.report_job(experiment_ctx, stats_ids[1], stats_ids[0])
    report_job = StageJob(
        job_id=report_ids[0],
        stage=StageKind.REPORT_GENERATION,
        context=experiment_ctx,
        inputs=report_ids[2],
        output=report_ids[1],
        dependencies=report_ids[3],
    )
    jobs.append(report_job)

    planning_graph = PlanningGraph(tuple(jobs))
    planning_graph.validate_acyclic()
    return planning_graph
