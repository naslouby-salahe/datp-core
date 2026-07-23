"""Demand-driven stage job derivation, seed expansion, and pre-execution plan validation."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from attrs import define

from datp_core.artifacts.models import ArtifactKey, ArtifactKind
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.datasets.models import PartitionSeedContract
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import ConditionSweepRecord, EvidenceRole, ExperimentRecord, SweepConditionRecord, ValueSweepRecord
from datp_core.pipeline.identifiers import ExperimentId, JobId
from datp_core.pipeline.models import PlanningGraph, StageJob, StageJobContext, StageKind
from datp_core.pipeline.values import PositiveInt


def _sweep_values(experiment: ExperimentRecord, name: str | None) -> tuple[float, ...]:
    return tuple(
        float(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == name
        for value in sweep.values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )


def _sweep_reference(overrides, name: str) -> str | None:
    override = None if overrides is None else overrides.get(name)
    reference = override.get("from_sweep") if isinstance(override, Mapping) else None
    return reference if isinstance(reference, str) else None


def _evaluation_sweep_values(experiment: ExperimentRecord, overrides, name: str) -> tuple[float | None, ...]:
    return _sweep_values(experiment, _sweep_reference(overrides, name)) or (None,)


def _feature_sweep_values(experiment: ExperimentRecord, overrides) -> tuple[tuple[str, ...] | None, ...]:
    sweep_name = _sweep_reference(overrides, "fingerprint_features")
    values = tuple(
        value
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, tuple) and value and all(isinstance(feature, str) for feature in value)
    )
    return values or (None,)


def resolve_partition_contract(
    config: ResolvedProjectConfiguration, experiment_id: ExperimentId, condition_name: str | None
) -> tuple[SweepConditionRecord | None, PartitionSeedContract | None]:
    if condition_name is None:
        return (None, None)
    experiment = config.experiments.get(experiment_id)
    matches = tuple(
        condition
        for sweep in experiment.sweeps
        if isinstance(sweep, ConditionSweepRecord)
        for condition in sweep.conditions
        if condition.name == condition_name
    )
    if len(matches) != 1:
        raise ValueError(f"Experiment '{experiment_id.value}' has no unique partition condition '{condition_name}'")
    try:
        namespace = config.protocol_determinism.seed_namespaces["partition"]
        digest_bytes = PositiveInt(int(config.protocol_determinism.derived_seed_algorithm["digest_bytes"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Protocol determinism lacks a valid partition seed namespace") from exc
    return (matches[0], PartitionSeedContract(key=namespace.key, digest_bytes=digest_bytes))


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
    mu_sweep_name = _sweep_reference(experiment.training_overrides, "mu")
    mus = _sweep_values(experiment, mu_sweep_name) or (None,)
    training_profile = config.training_profiles.get(experiment.training_profile_id)
    ditto_weights = (
        training_profile.personalization_parameter_grid or (None,)
        if training_profile.personalization == "ditto"
        else (None,)
    )

    # 2. Materialize once per seed, condition, and population, then collect every training cell.
    training_cells: list[tuple[StageJobContext, tuple, tuple]] = []
    for seed, condition, population_id in product(seed_cohort.training_seeds, conditions, experiment.population_ids):
        materialization_ctx = StageJobContext(
            experiment_id=experiment.identifier,
            seed=int(seed.value),
            partition_condition=condition,
            population_id=population_id,
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
                population_id=population_id,
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

    # 3. Derive immutable score artifacts, then select each evaluation's declared population and calibration window.
    calibration_cells_by_training: dict[tuple[int | None, str | None, float | None, float | None, object], list] = {}
    score_cells: dict[tuple[int | None, str | None, float | None, float | None, object], tuple] = {}
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
                        job_id=subset_ids[0],
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
        if materialization.split_method == "within_client_chronological":
            future_ids = builder.future_recalibration_score_job(
                seed_ctx, train_ids[1], mat_ids[1], train_ids[0], selection_output, selection_job_id
            )
            jobs.append(
                StageJob(
                    job_id=future_ids[0],
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
            if eval_spec.recalibration_mode == "one_shot":
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
                            job_id=thresh_ids[0],
                            stage=StageKind.THRESHOLD_CONSTRUCTION,
                            context=eval_ctx,
                            inputs=thresh_ids[2],
                            output=thresh_ids[1],
                            dependencies=thresh_ids[3],
                        )
                    )
                    eval_ids = builder.evaluation_job(eval_ctx, thresh_ids[1], test_ids[1], thresh_ids[0], test_ids[0])
                    jobs.append(
                        StageJob(
                            job_id=eval_ids[0],
                            stage=StageKind.OPERATING_POINT_EVALUATION,
                            context=eval_ctx,
                            inputs=eval_ids[2],
                            output=eval_ids[1],
                            dependencies=eval_ids[3],
                        )
                    )
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


@define(frozen=True, slots=True, kw_only=True)
class PlanValidationResult:
    is_valid: bool
    errors: tuple[str, ...]
    job_count: int
    dependency_count: int


class ExecutionPlanValidator:
    """Validator performing deep structural and artifact contract checks on planning graphs."""

    @staticmethod
    def _build_producer_map(graph: PlanningGraph, errors: list[str]) -> dict[ArtifactKey, JobId]:
        producers: dict[ArtifactKey, JobId] = {}
        for job in graph.jobs:
            if job.output in producers:
                errors.append(f"Multiple producers found for artifact output '{job.output.artifact_id}'")
            producers[job.output] = job.job_id
        return producers

    def validate(self, graph: PlanningGraph) -> PlanValidationResult:
        errors: list[str] = []

        if graph.node_count == 0:
            errors.append("Planning graph contains no job nodes")
            return PlanValidationResult(
                is_valid=False,
                errors=tuple(errors),
                job_count=0,
                dependency_count=0,
            )

        # Check acyclicity
        try:
            graph.validate_acyclic()
        except ValueError as exc:
            errors.append(str(exc))

        # Check job node count vs topological sort
        top_order = graph.lexicographical_topological_sort()
        if len(top_order) != graph.node_count:
            errors.append("Topological sort node count mismatch")

        producers = self._build_producer_map(graph, errors)
        self._validate_job_inputs(graph, producers, errors)

        is_valid = len(errors) == 0
        return PlanValidationResult(
            is_valid=is_valid,
            errors=tuple(errors),
            job_count=graph.node_count,
            dependency_count=graph.edge_count,
        )


    @staticmethod
    def _validate_job_inputs(graph: PlanningGraph, producers: dict[ArtifactKey, JobId], errors: list[str]) -> None:
        for job in graph.jobs:
            for inp in job.inputs:
                if inp not in producers:
                    errors.append(
                        f"Job '{job.job_id}' consumes artifact '{inp.artifact_id}' which has no producer in the plan"
                    )

            if job.stage is StageKind.THRESHOLD_CONSTRUCTION and any(
                item.kind is ArtifactKind.TEST_SCORES for item in job.inputs
            ):
                errors.append(f"Threshold job '{job.job_id}' must not consume test scores")
            if job.stage is StageKind.OPERATING_POINT_EVALUATION and any(
                item.kind in {ArtifactKind.CALIBRATION_SCORES, ArtifactKind.FUTURE_RECALIBRATION_SCORES}
                for item in job.inputs
            ):
                errors.append(f"Evaluation job '{job.job_id}' must not consume calibration scores")


def validate_planning_graph(graph: PlanningGraph) -> None:
    validator = ExecutionPlanValidator()
    res = validator.validate(graph)
    if not res.is_valid:
        raise ValueError(f"Planning graph validation failed: {res.errors}")
