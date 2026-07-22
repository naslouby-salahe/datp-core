"""Demand-driven stage job derivation and seed expansion logic."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.catalogue import ConditionSweepRecord, EvidenceRole, ExperimentRecord, ValueSweepRecord
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
    requested_mu_sweep = experiment.training_overrides.get("mu") if experiment.training_overrides is not None else None
    mu_sweep_name = requested_mu_sweep.get("from_sweep") if isinstance(requested_mu_sweep, Mapping) else None
    mus = tuple(
        float(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == mu_sweep_name
        for value in sweep.values
        if isinstance(value, float)
    ) or (None,)
    training_profile = config.training_profiles.get(experiment.training_profile_id)
    ditto_weights = (
        training_profile.personalization_parameter_grid or (None,)
        if training_profile.personalization == "ditto"
        else (None,)
    )

    # 2. Materialize once per seed/partition condition, then collect every training cell.
    training_cells: list[tuple[StageJobContext, tuple, tuple]] = []
    for seed, condition in product(seed_cohort.training_seeds, conditions):
        materialization_ctx = StageJobContext(
            experiment_id=experiment.identifier,
            seed=int(seed.value),
            partition_condition=condition,
        )
        mat_ids = builder.materialization_job(materialization_ctx, pf_output, pf_job_id)
        mat_job = StageJob(
            job_id=mat_ids[0],
            stage=StageKind.DATASET_MATERIALIZATION,
            context=materialization_ctx,
            inputs=mat_ids[2],
            output=mat_ids[1],
            dependencies=mat_ids[3],
        )
        jobs.append(mat_job)

        for proximal_mu, ditto_weight in product(mus, ditto_weights):
            seed_ctx = StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                partition_condition=condition,
                federated_proximal_mu=proximal_mu,
                ditto_proximal_weight=ditto_weight,
            )
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
            training_cells.append((seed_ctx, mat_ids, train_ids))

    selection_output = None
    selection_job_id = None
    analysis_selection_output = None
    analysis_selection_job_id = None
    if (
        experiment.evidence_role is EvidenceRole.CONFIRMATORY
        and training_profile.checkpoint_authorization == "primary_selection_computed_once_on_natural_device_regime"
    ):
        selection_ids = builder.cohort_checkpoint_selection_job(
            experiment_ctx,
            tuple(train_ids[1] for _, _, train_ids in training_cells),
            tuple(train_ids[0] for _, _, train_ids in training_cells),
        )
        jobs.append(
            StageJob(
                job_id=selection_ids[0],
                stage=StageKind.CHECKPOINT_SELECTION,
                context=experiment_ctx,
                inputs=selection_ids[2],
                output=selection_ids[1],
                dependencies=selection_ids[3],
            )
        )
        selection_job_id, selection_output = selection_ids[:2]
    elif training_profile.kind == "federated_prox_training":
        selection_ids = builder.federated_proximal_selection_job(
            experiment_ctx,
            tuple(train_ids[1] for _, _, train_ids in training_cells),
            tuple(train_ids[0] for _, _, train_ids in training_cells),
        )
        jobs.append(
            StageJob(
                job_id=selection_ids[0],
                stage=StageKind.CHECKPOINT_SELECTION,
                context=experiment_ctx,
                inputs=selection_ids[2],
                output=selection_ids[1],
                dependencies=selection_ids[3],
            )
        )
        analysis_selection_job_id, analysis_selection_output = selection_ids[:2]
    elif (
        training_profile.personalization == "ditto"
        and experiment.identifier == config.primary_ditto_selection_experiment().identifier
    ):
        selection_ids = builder.ditto_selection_job(
            experiment_ctx,
            tuple(train_ids[1] for _, _, train_ids in training_cells),
            tuple(train_ids[0] for _, _, train_ids in training_cells),
        )
        jobs.append(
            StageJob(
                job_id=selection_ids[0],
                stage=StageKind.CHECKPOINT_SELECTION,
                context=experiment_ctx,
                inputs=selection_ids[2],
                output=selection_ids[1],
                dependencies=selection_ids[3],
            )
        )
        analysis_selection_job_id, analysis_selection_output = selection_ids[:2]

    # 3. Derive score, threshold, and evaluation jobs from the collected training cells.
    for seed_ctx, mat_ids, train_ids in training_cells:
        calib_ids = builder.calibration_score_job(
            seed_ctx, train_ids[1], mat_ids[1], train_ids[0], selection_output, selection_job_id
        )
        calib_score_job = StageJob(
            job_id=calib_ids[0],
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            inputs=calib_ids[2],
            output=calib_ids[1],
            dependencies=calib_ids[3],
        )
        jobs.append(calib_score_job)

        test_ids = builder.test_score_job(
            seed_ctx, train_ids[1], mat_ids[1], train_ids[0], selection_output, selection_job_id
        )
        test_score_job = StageJob(
            job_id=test_ids[0],
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            inputs=test_ids[2],
            output=test_ids[1],
            dependencies=test_ids[3],
        )
        jobs.append(test_score_job)

        for eval_spec in experiment.evaluations:
            override = None if eval_spec.overrides is None else eval_spec.overrides.get("quantile")
            sweep_name = override.get("from_sweep") if isinstance(override, Mapping) else None
            quantiles = tuple(
                float(value)
                for sweep in experiment.sweeps
                if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
                for value in sweep.values
                if isinstance(value, float)
            ) or (None,)
            shrinkage_override = None if eval_spec.overrides is None else eval_spec.overrides.get("shrinkage_weight")
            shrinkage_sweep = shrinkage_override.get("from_sweep") if isinstance(shrinkage_override, Mapping) else None
            shrinkage_weights = tuple(
                float(value)
                for sweep in experiment.sweeps
                if isinstance(sweep, ValueSweepRecord) and sweep.name == shrinkage_sweep
                for value in sweep.values
                if isinstance(value, float)
            ) or (None,)
            fixed_k_override = None if eval_spec.overrides is None else eval_spec.overrides.get("fixed_k")
            fixed_k_sweep = fixed_k_override.get("from_sweep") if isinstance(fixed_k_override, Mapping) else None
            fixed_ks = tuple(
                float(value)
                for sweep in experiment.sweeps
                if isinstance(sweep, ValueSweepRecord) and sweep.name == fixed_k_sweep
                for value in sweep.values
                if isinstance(value, float)
            ) or (None,)
            for threshold_quantile, shrinkage_weight, fixed_k in product(quantiles, shrinkage_weights, fixed_ks):
                eval_ctx = StageJobContext(
                    experiment_id=experiment.identifier,
                    seed=seed_ctx.seed,
                    partition_condition=seed_ctx.partition_condition,
                    federated_proximal_mu=seed_ctx.federated_proximal_mu,
                    ditto_proximal_weight=seed_ctx.ditto_proximal_weight,
                    threshold_quantile=threshold_quantile,
                    shrinkage_weight=shrinkage_weight,
                    federated_summary_fixed_k=fixed_k,
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
    stats_ids = builder.statistical_analysis_job(
        experiment_ctx,
        tuple(eval_job_outputs),
        tuple(eval_job_ids),
        () if analysis_selection_output is None else (analysis_selection_output,),
        () if analysis_selection_job_id is None else (analysis_selection_job_id,),
    )
    stats_job = StageJob(
        job_id=stats_ids[0],
        stage=StageKind.STATISTICAL_ANALYSIS,
        context=experiment_ctx,
        inputs=stats_ids[2],
        output=stats_ids[1],
        dependencies=stats_ids[3],
    )
    jobs.append(stats_job)

    # 4. Freeze the complete result family before any rendering may begin.
    result_freeze_ids = builder.result_freeze_job(
        experiment_ctx,
        stats_ids[1],
        stats_ids[0],
        tuple(eval_job_outputs),
        tuple(eval_job_ids),
    )
    result_freeze_job = StageJob(
        job_id=result_freeze_ids[0],
        stage=StageKind.RESULT_FREEZE,
        context=experiment_ctx,
        inputs=result_freeze_ids[2],
        output=result_freeze_ids[1],
        dependencies=result_freeze_ids[3],
    )
    jobs.append(result_freeze_job)

    # 5. Report Generation job
    report_ids = builder.report_job(experiment_ctx, result_freeze_ids[1], result_freeze_ids[0])
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
