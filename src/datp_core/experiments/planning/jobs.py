"""Demand-driven experiment job expansion — materialization, training, scoring, evaluation, analysis."""

from __future__ import annotations

from itertools import product

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.data.contracts.enums import SplitMethod
from datp_core.experiments.catalogue.evaluations import RecalibrationMode
from datp_core.experiments.catalogue.models import EvidenceRole, ExperimentRecord
from datp_core.experiments.catalogue.sweeps import ConditionSweepRecord
from datp_core.experiments.identity.builder import IdentityBuilder
from datp_core.experiments.planning.sweeps import (
    _evaluation_sweep_values,
    _feature_sweep_values,
    _sweep_reference,
    _sweep_values,
)
from datp_core.learning.contracts.enums import CheckpointAuthorization, PersonalizationStrategy, TrainingProfileKind
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob


def expand_experiment_jobs(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> PlanningGraph:
    seed_cohort = config.seed_cohorts.get(experiment.seed_cohort_id)
    builder = IdentityBuilder()
    jobs: list[StageJob] = []

    experiment_ctx = StageJobContext(experiment_id=experiment.identifier)

    # 1. Preflight check job
    pf_node_key, pf_output = builder.preflight_job(experiment_ctx)
    preflight_job = StageJob(
        node_key=pf_node_key,
        stage=StageKind.PREFLIGHT,
        context=experiment_ctx,
        inputs=(),
        output=pf_output,
        dependencies=(),
    )
    jobs.append(preflight_job)

    eval_outputs: list = []
    eval_node_keys: list = []
    conditions = tuple(
        condition.name
        for sweep in experiment.sweeps
        if isinstance(sweep, ConditionSweepRecord)
        for condition in sweep.conditions
    ) or (None,)
    mu_sweep_name = _sweep_reference(experiment.training_overrides, "mu")
    mus = _sweep_values(experiment, mu_sweep_name) or (None,)
    training_profile = config.training_profiles.get(experiment.training_profile_id)
    ditto_weights = (
        training_profile.personalization_parameter_grid or (None,)
        if training_profile.personalization == PersonalizationStrategy.DITTO
        else (None,)
    )

    training_cells: list[tuple[StageJobContext, tuple, tuple]] = []
    for seed, condition, population_id in product(seed_cohort.training_seeds, conditions, experiment.population_ids):
        materialization_ctx = StageJobContext(
            experiment_id=experiment.identifier,
            seed=int(seed.value),
            partition_condition=condition,
            population_id=population_id,
        )
        mat_ids = builder.materialization_job(materialization_ctx, pf_output, pf_node_key)
        mat_job = StageJob(
            node_key=mat_ids[0],
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
                population_id=population_id,
                federated_proximal_mu=proximal_mu,
                ditto_proximal_weight=ditto_weight,
            )
            train_ids = builder.training_job(seed_ctx, mat_ids[1], mat_ids[0])
            train_job = StageJob(
                node_key=train_ids[0],
                stage=StageKind.MODEL_TRAINING,
                context=seed_ctx,
                inputs=train_ids[2],
                output=train_ids[1],
                dependencies=train_ids[3],
            )
            jobs.append(train_job)
            training_cells.append((seed_ctx, mat_ids, train_ids))

    selection_output = None
    selection_node_key = None
    analysis_selection_output = None
    analysis_selection_node_key = None
    if (
        experiment.evidence_role is EvidenceRole.CONFIRMATORY
        and training_profile.checkpoint_authorization == CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE
    ):
        selection_ids = builder.cohort_checkpoint_selection_job(
            experiment_ctx,
            tuple(train_ids[1] for _, _, train_ids in training_cells),
            tuple(train_ids[0] for _, _, train_ids in training_cells),
        )
        jobs.append(
            StageJob(
                node_key=selection_ids[0],
                stage=StageKind.CHECKPOINT_SELECTION,
                context=experiment_ctx,
                inputs=selection_ids[2],
                output=selection_ids[1],
                dependencies=selection_ids[3],
            )
        )
        selection_node_key, selection_output = selection_ids[:2]
    elif training_profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
        selection_ids = builder.federated_proximal_selection_job(
            experiment_ctx,
            tuple(train_ids[1] for _, _, train_ids in training_cells),
            tuple(train_ids[0] for _, _, train_ids in training_cells),
        )
        jobs.append(
            StageJob(
                node_key=selection_ids[0],
                stage=StageKind.CHECKPOINT_SELECTION,
                context=experiment_ctx,
                inputs=selection_ids[2],
                output=selection_ids[1],
                dependencies=selection_ids[3],
            )
        )
        analysis_selection_node_key, analysis_selection_output = selection_ids[:2]
    elif (
        training_profile.personalization == PersonalizationStrategy.DITTO
        and experiment.identifier == config.primary_ditto_selection_experiment().identifier
    ):
        selection_ids = builder.ditto_selection_job(
            experiment_ctx,
            tuple(train_ids[1] for _, _, train_ids in training_cells),
            tuple(train_ids[0] for _, _, train_ids in training_cells),
        )
        jobs.append(
            StageJob(
                node_key=selection_ids[0],
                stage=StageKind.CHECKPOINT_SELECTION,
                context=experiment_ctx,
                inputs=selection_ids[2],
                output=selection_ids[1],
                dependencies=selection_ids[3],
            )
        )
        analysis_selection_node_key, analysis_selection_output = selection_ids[:2]

    # 3. Score generation and evaluation
    calibration_cells_by_training: dict[tuple[int | None, str | None, float | None, float | None, object], list] = {}
    score_cells: dict[tuple[int | None, str | None, float | None, float | None, object], tuple] = {}
    for seed_ctx, mat_ids, train_ids in training_cells:
        calib_ids = builder.calibration_score_job(
            seed_ctx, train_ids[1], mat_ids[1], train_ids[0], selection_output, selection_node_key
        )
        calib_score_job = StageJob(
            node_key=calib_ids[0],
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            inputs=calib_ids[2],
            output=calib_ids[1],
            dependencies=calib_ids[3],
        )
        jobs.append(calib_score_job)

        test_ids = builder.test_score_job(
            seed_ctx, train_ids[1], mat_ids[1], train_ids[0], selection_output, selection_node_key
        )
        test_score_job = StageJob(
            node_key=test_ids[0],
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            inputs=test_ids[2],
            output=test_ids[1],
            dependencies=test_ids[3],
        )
        jobs.append(test_score_job)

        calibration_cells = [(seed_ctx, calib_ids)]
        if experiment.calibration_subset is not None:
            requested_sweep = experiment.calibration_subset.requested_sample_count.get("from_sweep")
            requested_counts = _sweep_values(experiment, requested_sweep)
            if not requested_counts or any(not value.is_integer() or value < 1.0 for value in requested_counts):
                raise ValueError("Calibration subset requires a positive integer sample-count sweep")
            for requested_count, replicate in product(
                (int(value) for value in requested_counts), range(experiment.calibration_subset.replicate_count.value)
            ):
                subset_ctx = StageJobContext(
                    experiment_id=seed_ctx.experiment_id,
                    seed=seed_ctx.seed,
                    partition_condition=seed_ctx.partition_condition,
                    population_id=seed_ctx.population_id,
                    federated_proximal_mu=seed_ctx.federated_proximal_mu,
                    ditto_proximal_weight=seed_ctx.ditto_proximal_weight,
                    calibration_sample_count=requested_count,
                    calibration_replicate=replicate,
                )
                subset_ids = builder.calibration_subset_job(subset_ctx, calib_ids[1], calib_ids[0])
                jobs.append(
                    StageJob(
                        node_key=subset_ids[0],
                        stage=StageKind.CALIBRATION_SUBSAMPLING,
                        context=subset_ctx,
                        inputs=subset_ids[2],
                        output=subset_ids[1],
                        dependencies=subset_ids[3],
                    )
                )
                calibration_cells.append((subset_ctx, subset_ids))
        key = (
            seed_ctx.seed,
            seed_ctx.partition_condition,
            seed_ctx.federated_proximal_mu,
            seed_ctx.ditto_proximal_weight,
            seed_ctx.population_id,
        )
        calibration_cells_by_training[key] = calibration_cells
        score_cells[key] = (seed_ctx, test_ids)

        if seed_ctx.population_id is None:
            raise ValueError("Training cells require a resolved population")
        population = config.populations.get(seed_ctx.population_id)
        dataset = config.datasets.get(population.dataset_id)
        setup = dataset.setup(population.setup_id)
        materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
        if materialization.split_method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL:
            future_ids = builder.future_recalibration_score_job(
                seed_ctx, train_ids[1], mat_ids[1], train_ids[0], selection_output, selection_node_key
            )
            jobs.append(
                StageJob(
                    node_key=future_ids[0],
                    stage=StageKind.SCORE_GENERATION,
                    context=seed_ctx,
                    inputs=future_ids[2],
                    output=future_ids[1],
                    dependencies=future_ids[3],
                )
            )
            score_cells[key] = (seed_ctx, test_ids, future_ids)

    for key, (seed_ctx, test_ids, *future_score_ids) in score_cells.items():
        for eval_spec in experiment.evaluations:
            population_id = eval_spec.population_id or experiment.population_ids[0]
            if population_id != seed_ctx.population_id:
                continue
            calibration_cells = calibration_cells_by_training[key]
            if eval_spec.recalibration_mode is RecalibrationMode.ONE_SHOT:
                if len(future_score_ids) != 1:
                    raise ValueError(f"Evaluation '{eval_spec.label}' requires a temporal recalibration score artifact")
                calibration_cells = [(seed_ctx, future_score_ids[0])]
            for calibration_ctx, calibration_ids in calibration_cells:
                quantiles = _evaluation_sweep_values(experiment, eval_spec.overrides, "quantile")
                shrinkage_weights = _evaluation_sweep_values(experiment, eval_spec.overrides, "shrinkage_weight")
                fixed_ks = _evaluation_sweep_values(experiment, eval_spec.overrides, "fixed_k")
                fingerprint_feature_sets = _feature_sweep_values(experiment, eval_spec.overrides)
                for threshold_quantile, shrinkage_weight, fixed_k, fingerprint_features in product(
                    quantiles, shrinkage_weights, fixed_ks, fingerprint_feature_sets
                ):
                    eval_ctx = StageJobContext(
                        experiment_id=experiment.identifier,
                        seed=seed_ctx.seed,
                        partition_condition=seed_ctx.partition_condition,
                        federated_proximal_mu=seed_ctx.federated_proximal_mu,
                        ditto_proximal_weight=seed_ctx.ditto_proximal_weight,
                        calibration_sample_count=calibration_ctx.calibration_sample_count,
                        calibration_replicate=calibration_ctx.calibration_replicate,
                        threshold_quantile=threshold_quantile,
                        shrinkage_weight=shrinkage_weight,
                        federated_summary_fixed_k=fixed_k,
                        fingerprint_features=fingerprint_features,
                        evaluation_label=eval_spec.label,
                        population_id=population_id,
                        recalibration_mode=eval_spec.recalibration_mode,
                        threshold_policy_id=eval_spec.threshold_policy_id,
                    )
                    thresh_ids = builder.threshold_job(eval_ctx, calibration_ids[1], calibration_ids[0])
                    jobs.append(
                        StageJob(
                            node_key=thresh_ids[0],
                            stage=StageKind.THRESHOLD_CONSTRUCTION,
                            context=eval_ctx,
                            inputs=thresh_ids[2],
                            output=thresh_ids[1],
                            dependencies=thresh_ids[3],
                        )
                    )
                    eval_ids = builder.evaluation_job(
                        eval_ctx, thresh_ids[1], test_ids[1], thresh_ids[0], test_ids[0]
                    )
                    jobs.append(
                        StageJob(
                            node_key=eval_ids[0],
                            stage=StageKind.OPERATING_POINT_EVALUATION,
                            context=eval_ctx,
                            inputs=eval_ids[2],
                            output=eval_ids[1],
                            dependencies=eval_ids[3],
                        )
                    )
                    eval_outputs.append(eval_ids[1])
                    eval_node_keys.append(eval_ids[0])

    # 4. Statistical Analysis job
    stats_ids = builder.statistical_analysis_job(
        experiment_ctx,
        tuple(eval_outputs),
        tuple(eval_node_keys),
        () if analysis_selection_output is None else (analysis_selection_output,),
        () if analysis_selection_node_key is None else (analysis_selection_node_key,),
    )
    stats_job = StageJob(
        node_key=stats_ids[0],
        stage=StageKind.STATISTICAL_ANALYSIS,
        context=experiment_ctx,
        inputs=stats_ids[2],
        output=stats_ids[1],
        dependencies=stats_ids[3],
    )
    jobs.append(stats_job)

    # 5. Freeze result family
    result_freeze_ids = builder.result_freeze_job(
        experiment_ctx,
        stats_ids[1],
        stats_ids[0],
        tuple(eval_outputs),
        tuple(eval_node_keys),
    )
    result_freeze_job = StageJob(
        node_key=result_freeze_ids[0],
        stage=StageKind.RESULT_FREEZE,
        context=experiment_ctx,
        inputs=result_freeze_ids[2],
        output=result_freeze_ids[1],
        dependencies=result_freeze_ids[3],
    )
    jobs.append(result_freeze_job)

    # 6. Report Generation job
    report_ids = builder.report_job(experiment_ctx, result_freeze_ids[1], result_freeze_ids[0])
    report_job = StageJob(
        node_key=report_ids[0],
        stage=StageKind.REPORT_GENERATION,
        context=experiment_ctx,
        inputs=report_ids[2],
        output=report_ids[1],
        dependencies=report_ids[3],
    )
    jobs.append(report_job)

    planning_graph = PlanningGraph(tuple(jobs))
    validate_acyclic(planning_graph)
    return planning_graph
