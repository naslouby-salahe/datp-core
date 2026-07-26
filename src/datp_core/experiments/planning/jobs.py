"""Expand one experiment into an active DAG with explicit semantic file paths."""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import TYPE_CHECKING

from datp_core.config.fingerprinting.canonical import compute_fingerprint
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.data.contracts.enums import ClientConstructionMethod, SplitMethod
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint
from datp_core.experiments.catalogue.evaluations import RecalibrationMode
from datp_core.experiments.catalogue.models import EvidenceRole, ExperimentRecord
from datp_core.experiments.catalogue.sweeps import ConditionSweepRecord
from datp_core.experiments.planning.layout import cell_directory, evaluation_directory, output, shared_output_path
from datp_core.experiments.planning.sweeps import (
    _evaluation_sweep_values,
    _feature_sweep_values,
    _sweep_reference,
    _sweep_values,
)
from datp_core.learning.contracts.enums import CheckpointAuthorization, PersonalizationStrategy, TrainingProfileKind
from datp_core.learning.contracts.seeds import SeedCohortRecord
from datp_core.learning.contracts.training import TrainingProfileRecord
from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput, StageJob, StageOutput

if TYPE_CHECKING:
    from datp_core.analysis.execution.inputs import PrerequisiteExperimentResult


_SHAREABLE_STAGES = frozenset(
    {
        StageKind.DATASET_MATERIALIZATION,
        StageKind.MODEL_TRAINING,
        StageKind.CHECKPOINT_SELECTION,
        StageKind.SCORE_GENERATION,
    }
)

_SHARED_OUTPUT_DIRECTORIES = {
    StageKind.DATASET_MATERIALIZATION: "materializations",
    StageKind.MODEL_TRAINING: "training",
    StageKind.CHECKPOINT_SELECTION: "checkpoint-selection",
    StageKind.SCORE_GENERATION: "scores",
}


@dataclass(frozen=True, slots=True)
class SharedUpstreamKey:
    """Exact in-memory structural coordinates for one active campaign producer."""

    stage: StageKind
    dataset_id: object
    population_id: object | None
    materialization_id: object
    partition_condition: str | None
    seed: int | None
    seed_cohort_id: object
    training_profile_id: object
    training_overrides_fingerprint: str
    checkpoint_profile_id: object
    eligibility_policy_id: object
    readiness_gates: tuple[str, ...]
    score_output_name: str | None
    temporal_mode: str
    source_fingerprint: str
    direct_producers: tuple[tuple[GraphNodeKey, str], ...]


def _value(value: object | None) -> str:
    return "-" if value is None else str(getattr(value, "value", value))


def _node_key(stage: StageKind, context: StageJobContext, role: str) -> GraphNodeKey:
    """Build a deterministic key used only for this in-memory graph."""

    coordinates = (
        context.experiment_id,
        context.seed,
        context.population_id,
        context.partition_condition,
        context.federated_proximal_mu,
        context.ditto_proximal_weight,
        context.evaluation_label,
        context.threshold_policy_id,
        context.threshold_quantile,
        context.shrinkage_weight,
        context.federated_summary_fixed_k,
        context.fingerprint_features,
        context.calibration_sample_count,
        context.calibration_replicate,
        context.recalibration_mode,
    )
    return GraphNodeKey(label="|".join((stage.value, role, *(_value(value) for value in coordinates))))


def _input(name: str, job: StageJob, output_name: str) -> StageInput:
    return StageInput(name=name, relative_path=job.output_path(output_name), producer=job.node_key)


def _job(
    *,
    stage: StageKind,
    context: StageJobContext,
    role: str,
    inputs: tuple[StageInput, ...] = (),
    outputs: tuple[StageOutput, ...],
    dependencies: tuple[GraphNodeKey, ...] = (),
) -> StageJob:
    experiment_prefix = f"experiments/{context.experiment_id.value}/"
    return StageJob(
        node_key=_node_key(stage, context, role),
        stage=stage,
        context=context,
        inputs=inputs,
        outputs=tuple(
            StageOutput(name=item.name, relative_path=experiment_prefix + item.relative_path) for item in outputs
        ),
        dependencies=dependencies,
    )


def _training_outputs(context: StageJobContext, *, personalized: bool) -> tuple[StageOutput, ...]:
    base = f"training/{cell_directory(context)}"
    results = [
        output("checkpoint", f"{base}/checkpoint.safetensors"),
        output("selection_evidence", f"{base}/selection-evidence.json"),
    ]
    if personalized:
        results.append(output("personalized_checkpoint",
                       f"{base}/personalized-checkpoint.safetensors"))
    return tuple(results)


def _score_output(context: StageJobContext, name: str) -> StageOutput:
    return output(name, f"scores/{cell_directory(context)}/{name.replace('_', '-')}.parquet")


def _create_training_cells(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
    experiment_ctx: StageJobContext,
    preflight: StageJob,
    seed_cohort: SeedCohortRecord,
    conditions: tuple[str | None, ...],
    mus: tuple[float | None, ...],
    ditto_weights: tuple[float | None, ...],
    training_profile: TrainingProfileRecord,
) -> tuple[list[StageJob], list[tuple[StageJobContext, StageJob, StageJob]]]:
    jobs: list[StageJob] = []
    training_cells: list[tuple[StageJobContext, StageJob, StageJob]] = []
    for seed, condition, population_id in product(seed_cohort.training_seeds, conditions, experiment.population_ids):
        materialization_ctx = StageJobContext(
            experiment_id=experiment.identifier,
            seed=int(seed.value),
            partition_condition=condition,
            population_id=population_id,
        )
        materialization_base = f"materializations/{cell_directory(materialization_ctx)}"
        materialization_outputs = [
            output("dataset", f"{materialization_base}/dataset.parquet"),
            output("split_manifest", f"{materialization_base}/split-manifest.json"),
            output("readiness", f"{materialization_base}/readiness.json"),
            output("preprocessing", f"{materialization_base}/preprocessing.json"),
        ]
        population = config.populations.get(population_id)
        dataset = config.datasets.get(population.dataset_id)
        setup = dataset.setup(population.setup_id)
        if setup.client_construction.method is ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS:
            materialization_outputs.append(
                output("partition_manifest", f"{materialization_base}/partition-manifest.json")
            )
        materialization = _job(
            stage=StageKind.DATASET_MATERIALIZATION,
            context=materialization_ctx,
            role="materialization",
            inputs=(_input("resolved_configuration", preflight, "resolved_configuration"),),
            outputs=tuple(materialization_outputs),
            dependencies=(preflight.node_key,),
        )
        jobs.append(materialization)

        for proximal_mu, ditto_weight in product(mus, ditto_weights):
            seed_ctx = StageJobContext(
                experiment_id=experiment.identifier,
                seed=int(seed.value),
                partition_condition=condition,
                population_id=population_id,
                federated_proximal_mu=proximal_mu,
                ditto_proximal_weight=ditto_weight,
            )
            training = _job(
                stage=StageKind.MODEL_TRAINING,
                context=seed_ctx,
                role="training",
                inputs=(_input("materialization", materialization, "dataset"),),
                outputs=_training_outputs(
                    seed_ctx, personalized=training_profile.personalization is PersonalizationStrategy.DITTO
                ),
                dependencies=(materialization.node_key,),
            )
            jobs.append(training)
            training_cells.append((seed_ctx, materialization, training))
    return jobs, training_cells


def _create_selection_stage(
    experiment: ExperimentRecord,
    training_profile: TrainingProfileRecord,
    config: ResolvedProjectConfiguration,
    experiment_ctx: StageJobContext,
    training_cells: list[tuple[StageJobContext, StageJob, StageJob]],
) -> StageJob | None:
    role: str | None
    if (
        experiment.evidence_role is EvidenceRole.CONFIRMATORY
        and training_profile.checkpoint_authorization is CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE
    ):
        role = "cohort"
    elif training_profile.kind is TrainingProfileKind.FEDERATED_PROX_TRAINING:
        role = "fedprox"
    elif (
        training_profile.personalization is PersonalizationStrategy.DITTO
        and experiment.identifier == config.primary_ditto_selection_experiment().identifier
    ):
        role = "ditto"
    else:
        return None

    inputs: list[StageInput] = []
    for index, (_, _, training) in enumerate(training_cells):
        inputs.extend(
            (
                _input(f"checkpoint_{index}", training, "checkpoint"),
                _input(f"selection_evidence_{index}", training, "selection_evidence"),
            )
        )
    return _job(
        stage=StageKind.CHECKPOINT_SELECTION,
        context=experiment_ctx,
        role=role,
        inputs=tuple(inputs),
        outputs=(output("checkpoint_selection", f"checkpoint-selection/{role}.json"),),
        dependencies=tuple(training.node_key for _, _, training in training_cells),
    )


def _create_scoring_and_calibration_cells(
    experiment: ExperimentRecord,
    training_cells: list[tuple[StageJobContext, StageJob, StageJob]],
    selection: StageJob | None,
    config: ResolvedProjectConfiguration,
) -> tuple[
    list[StageJob],
    dict[tuple[object, ...], list[tuple[StageJobContext, StageJob, str]]],
    dict[tuple[object, ...], tuple[StageJobContext, StageJob, StageJob, StageJob | None]],
]:
    jobs: list[StageJob] = []
    calibration_cells_by_training: dict[tuple[object, ...], list[tuple[StageJobContext, StageJob, str]]] = {}
    score_cells: dict[tuple[object, ...], tuple[StageJobContext, StageJob, StageJob, StageJob | None]] = {}
    for seed_ctx, materialization, training in training_cells:
        scoring_inputs = [
            _input("checkpoint", training, "checkpoint"),
            _input("materialization", materialization, "dataset"),
            _input("selection_evidence", training, "selection_evidence"),
        ]
        if any(item.name == "personalized_checkpoint" for item in training.outputs):
            scoring_inputs.append(_input("personalized_checkpoint", training, "personalized_checkpoint"))
        dependencies = [training.node_key, materialization.node_key]
        if selection is not None:
            scoring_inputs.append(_input("checkpoint_selection", selection, "checkpoint_selection"))
            dependencies.append(selection.node_key)

        calibration = _job(
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            role="calibration-scores",
            inputs=tuple(scoring_inputs),
            outputs=(_score_output(seed_ctx, "calibration_scores"),),
            dependencies=tuple(dependencies),
        )
        test = _job(
            stage=StageKind.SCORE_GENERATION,
            context=seed_ctx,
            role="test-scores",
            inputs=tuple(scoring_inputs),
            outputs=(_score_output(seed_ctx, "test_scores"),),
            dependencies=tuple(dependencies),
        )
        jobs.extend((calibration, test))

        calibration_cells: list[tuple[StageJobContext, StageJob, str]] = [(seed_ctx, calibration, "calibration_scores")]
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
                subset = _job(
                    stage=StageKind.CALIBRATION_SUBSAMPLING,
                    context=subset_ctx,
                    role="calibration-subset",
                    inputs=(_input("calibration_scores", calibration, "calibration_scores"),),
                    outputs=(
                        output(
                            "calibration_subset_scores",
                            f"calibration-subsets/{cell_directory(subset_ctx)}/"
                            f"n-{requested_count}-rep-{replicate}/scores.parquet",
                        ),
                    ),
                    dependencies=(calibration.node_key,),
                )
                jobs.append(subset)
                calibration_cells.append((subset_ctx, subset, "calibration_subset_scores"))

        key = (
            seed_ctx.seed,
            seed_ctx.partition_condition,
            seed_ctx.federated_proximal_mu,
            seed_ctx.ditto_proximal_weight,
            seed_ctx.population_id,
        )
        future: StageJob | None = None
        if seed_ctx.population_id is None:
            raise ValueError("Training cells require a resolved population")
        population = config.populations.get(seed_ctx.population_id)
        dataset = config.datasets.get(population.dataset_id)
        setup = dataset.setup(population.setup_id)
        materialization_contract = next(
            item for item in dataset.materializations if item.identifier == setup.materialization_id
        )
        if materialization_contract.split_method is SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL:
            future = _job(
                stage=StageKind.SCORE_GENERATION,
                context=seed_ctx,
                role="future-recalibration-scores",
                inputs=tuple(scoring_inputs),
                outputs=(_score_output(seed_ctx, "future_recalibration_scores"),),
                dependencies=tuple(dependencies),
            )
            jobs.append(future)
        calibration_cells_by_training[key] = calibration_cells
        score_cells[key] = (seed_ctx, test, calibration, future)
    return jobs, calibration_cells_by_training, score_cells


def _create_evaluation_jobs(
    experiment: ExperimentRecord,
    score_cells: dict[tuple[object, ...], tuple[StageJobContext, StageJob, StageJob, StageJob | None]],
    calibration_cells_by_training: dict[tuple[object, ...], list[tuple[StageJobContext, StageJob, str]]],
) -> tuple[list[StageJob], list[StageJob]]:
    jobs: list[StageJob] = []
    evaluation_jobs: list[StageJob] = []
    for key, (seed_ctx, test, _calibration, future) in score_cells.items():
        for evaluation in experiment.evaluations:
            population_id = evaluation.population_id or experiment.population_ids[0]
            if population_id != seed_ctx.population_id:
                continue
            calibration_cells = calibration_cells_by_training[key]
            if evaluation.recalibration_mode is RecalibrationMode.ONE_SHOT:
                if future is None:
                    raise ValueError(
                        f"Evaluation '{evaluation.label}' requires a temporal recalibration score artifact"
                    )
                calibration_cells = [(seed_ctx, future, "future_recalibration_scores")]
            for calibration_ctx, calibration_job, calibration_output in calibration_cells:
                for quantile, shrinkage, fixed_k, features in product(
                    _evaluation_sweep_values(experiment, evaluation.overrides, "quantile"),
                    _evaluation_sweep_values(experiment, evaluation.overrides, "shrinkage_weight"),
                    _evaluation_sweep_values(experiment, evaluation.overrides, "fixed_k"),
                    _feature_sweep_values(experiment, evaluation.overrides),
                ):
                    evaluation_ctx = StageJobContext(
                        experiment_id=experiment.identifier,
                        seed=seed_ctx.seed,
                        partition_condition=seed_ctx.partition_condition,
                        federated_proximal_mu=seed_ctx.federated_proximal_mu,
                        ditto_proximal_weight=seed_ctx.ditto_proximal_weight,
                        calibration_sample_count=calibration_ctx.calibration_sample_count,
                        calibration_replicate=calibration_ctx.calibration_replicate,
                        threshold_quantile=quantile,
                        shrinkage_weight=shrinkage,
                        federated_summary_fixed_k=fixed_k,
                        fingerprint_features=features,
                        evaluation_label=evaluation.label,
                        population_id=population_id,
                        recalibration_mode=evaluation.recalibration_mode,
                        threshold_policy_id=evaluation.threshold_policy_id,
                    )
                    evaluation_base = evaluation_directory(evaluation_ctx)
                    threshold = _job(
                        stage=StageKind.THRESHOLD_CONSTRUCTION,
                        context=evaluation_ctx,
                        role="thresholds",
                        inputs=(_input(calibration_output, calibration_job, calibration_output),),
                        outputs=(
                            output("thresholds", f"thresholds/{evaluation_base}/thresholds.parquet"),
                            output("diagnostics", f"thresholds/{evaluation_base}/diagnostics.json"),
                        ),
                        dependencies=(calibration_job.node_key,),
                    )
                    metrics = _job(
                        stage=StageKind.OPERATING_POINT_EVALUATION,
                        context=evaluation_ctx,
                        role="metrics",
                        inputs=(
                            _input("thresholds", threshold, "thresholds"),
                            _input("test_scores", test, "test_scores"),
                        ),
                        outputs=(output("client_metrics", f"evaluations/{evaluation_base}/client-metrics.parquet"),),
                        dependencies=(threshold.node_key, test.node_key),
                    )
                    jobs.extend((threshold, metrics))
                    evaluation_jobs.append(metrics)
    return jobs, evaluation_jobs


def expand_experiment_jobs(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
    *,
    prerequisite_results: tuple[PrerequisiteExperimentResult, ...] = (),
) -> PlanningGraph:
    seed_cohort = config.seed_cohorts.get(experiment.seed_cohort_id)
    jobs: list[StageJob] = []
    experiment_ctx = StageJobContext(experiment_id=experiment.identifier)

    preflight = _job(
        stage=StageKind.PREFLIGHT,
        context=experiment_ctx,
        role="resolved-configuration",
        outputs=(output("resolved_configuration", "preflight/resolved-configuration.json"),),
    )
    jobs.append(preflight)

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
        if training_profile.personalization is PersonalizationStrategy.DITTO
        else (None,)
    )

    training_jobs, training_cells = _create_training_cells(
        experiment, config, experiment_ctx, preflight, seed_cohort, conditions, mus, ditto_weights, training_profile
    )
    jobs.extend(training_jobs)

    selection = _create_selection_stage(experiment, training_profile, config, experiment_ctx, training_cells)
    if selection is not None:
        jobs.append(selection)

    scoring_jobs, calibration_cells_by_training, score_cells = _create_scoring_and_calibration_cells(
        experiment, training_cells, selection, config
    )
    jobs.extend(scoring_jobs)

    eval_jobs_result, evaluation_jobs = _create_evaluation_jobs(experiment, score_cells, calibration_cells_by_training)
    jobs.extend(eval_jobs_result)

    # Analysis receives every current-run scientific input explicitly.  It may inspect
    # only these declared direct dependencies; it never reconstructs a stage path.
    statistics_inputs = [
        StageInput(
            name=f"analysis_input_{index}_{stage_output.name}",
            relative_path=stage_output.relative_path,
            producer=stage_job.node_key,
            coordinates=AnalysisInputCoordinates(
                producer_stage=stage_job.stage,
                output_name=stage_output.name,
                context=stage_job.context,
            ),
        )
        for index, stage_job in enumerate(jobs)
        for stage_output in stage_job.outputs
    ]
    statistics_dependencies = [stage_job.node_key for stage_job in jobs]
    statistics = _job(
        stage=StageKind.STATISTICAL_ANALYSIS,
        context=StageJobContext(
            experiment_id=experiment.identifier,
            prerequisite_results=prerequisite_results,
        ),
        role="statistics",
        inputs=tuple(statistics_inputs),
        outputs=(output("statistical_result", "analysis/statistical-result.json"),),
        dependencies=tuple(statistics_dependencies),
    )
    jobs.append(statistics)

    freeze_inputs = [_input("statistical_result", statistics, "statistical_result")]
    freeze_inputs.extend(
        _input(f"client_metrics_{index}", metrics, "client_metrics") for index, metrics in enumerate(evaluation_jobs)
    )
    result_freeze = _job(
        stage=StageKind.RESULT_FREEZE,
        context=experiment_ctx,
        role="frozen-result",
        inputs=tuple(freeze_inputs),
        outputs=(output("frozen_result", "frozen-result.json"),),
        dependencies=(statistics.node_key, *(metrics.node_key for metrics in evaluation_jobs)),
    )
    jobs.append(result_freeze)
    report = _job(
        stage=StageKind.REPORT_GENERATION,
        context=experiment_ctx,
        role="report",
        inputs=(_input("frozen_result", result_freeze, "frozen_result"),),
        outputs=(output("report", "reports/report.md"),),
        dependencies=(result_freeze.node_key,),
    )
    jobs.append(report)

    graph = PlanningGraph(tuple(jobs))
    validate_acyclic(graph)
    return graph


def expand_campaign_jobs(
    experiments: tuple[ExperimentRecord, ...],
    config: ResolvedProjectConfiguration,
    *,
    prerequisite_results_by_experiment: dict[object,
        tuple[PrerequisiteExperimentResult, ...]] | None = None,
) -> PlanningGraph:
    """Build one active-campaign DAG with direct edges to exact shared producers.

    The producer map is deliberately local to this planning call.  It records no execution
    outcome and cannot be consulted by a later command.
    """

    source_fingerprints: dict[object, str] = {}
    shared_producers: dict[SharedUpstreamKey, StageJob] = {}
    rewritten_jobs: list[StageJob] = []
    output_paths: dict[tuple[GraphNodeKey, str], str] = {}
    node_keys: dict[GraphNodeKey, GraphNodeKey] = {}
    shared_ordinal = 0

    for experiment in experiments:
        prerequisite_results = (prerequisite_results_by_experiment or {}
                                ).get(experiment.identifier, ())
        graph = expand_experiment_jobs(
            experiment, config, prerequisite_results=prerequisite_results)
        for job in graph.jobs:
            inputs = tuple(
                replace(
                    item,
                    producer=node_keys.get(item.producer, item.producer),
                    relative_path=output_paths.get((item.producer, item.name), item.relative_path),
                )
                for item in job.inputs
            )
            dependencies = tuple(dict.fromkeys(node_keys.get(item, item)
                                 for item in job.dependencies))
            candidate = replace(job, inputs=inputs, dependencies=dependencies)
            if candidate.stage not in _SHAREABLE_STAGES:
                rewritten_jobs.append(candidate)
                node_keys[job.node_key] = candidate.node_key
                for stage_output in candidate.outputs:
                    output_paths[(job.node_key, stage_output.name)] = stage_output.relative_path
                continue

            key = _shared_upstream_key(candidate, config=config,
                                       source_fingerprints=source_fingerprints)
            producer = shared_producers.get(key)
            if producer is not None:
                node_keys[job.node_key] = producer.node_key
                for stage_output in producer.outputs:
                    output_paths[(job.node_key, stage_output.name)] = stage_output.relative_path
                continue

            shared_ordinal += 1
            producer = replace(
                candidate,
                node_key=GraphNodeKey(label=f"shared:{candidate.stage.value}:{shared_ordinal:04d}"),
                outputs=tuple(
                    StageOutput(
                        name=stage_output.name,
                        relative_path=shared_output_path(
                            directory=_SHARED_OUTPUT_DIRECTORIES[candidate.stage],
                            ordinal=shared_ordinal,
                            output_name=stage_output.name,
                            source_path=stage_output.relative_path,
                        ),
                    )
                    for stage_output in candidate.outputs
                ),
            )
            shared_producers[key] = producer
            rewritten_jobs.append(producer)
            node_keys[job.node_key] = producer.node_key
            for stage_output in producer.outputs:
                output_paths[(job.node_key, stage_output.name)] = stage_output.relative_path

    freeze_jobs = {
        job.context.experiment_id: job for job in rewritten_jobs if job.stage is StageKind.RESULT_FREEZE}
    campaign_jobs: list[StageJob] = []
    for job in rewritten_jobs:
        experiment = config.experiments.get(job.context.experiment_id)
        if job.stage is not StageKind.STATISTICAL_ANALYSIS or not experiment.prerequisites:
            campaign_jobs.append(job)
            continue
        prerequisite_inputs: list[StageInput] = []
        prerequisite_dependencies: list[GraphNodeKey] = []
        for prerequisite in experiment.prerequisites:
            freeze = freeze_jobs.get(prerequisite.experiment_id)
            if freeze is None:
                raise ValueError(
                    f"Campaign graph lacks frozen result for prerequisite '{prerequisite.experiment_id.value}'"
                )
            prerequisite_inputs.append(
                StageInput(
                    name=f"prerequisite_frozen_result_{prerequisite.experiment_id.value}",
                    relative_path=freeze.output_path("frozen_result"),
                    producer=freeze.node_key,
                    coordinates=AnalysisInputCoordinates(
                        producer_stage=StageKind.RESULT_FREEZE,
                        output_name="frozen_result",
                        context=freeze.context,
                    ),
                )
            )
            prerequisite_dependencies.append(freeze.node_key)
        campaign_jobs.append(
            replace(
                job,
                inputs=(*job.inputs, *prerequisite_inputs),
                dependencies=(*job.dependencies, *prerequisite_dependencies),
            )
        )

    graph = PlanningGraph(tuple(campaign_jobs))
    validate_acyclic(graph)
    return graph


def _shared_upstream_key(
    job: StageJob,
    *,
    config: ResolvedProjectConfiguration,
    source_fingerprints: dict[object, str],
) -> SharedUpstreamKey:
    experiment = config.experiments.get(job.context.experiment_id)
    population_id = job.context.population_id or experiment.population_ids[0]
    population = config.populations.get(population_id)
    dataset = config.datasets.get(population.dataset_id)
    setup = dataset.setup(population.setup_id)
    materialization = next(
        item for item in dataset.materializations if item.identifier == setup.materialization_id)
    source_fingerprint = source_fingerprints.get(dataset.dataset_id)
    if source_fingerprint is None:
        source_fingerprint = compute_experiment_source_fingerprint(
            datasets=config.datasets, dataset_ids=(dataset.dataset_id,)
        ).value
        source_fingerprints[dataset.dataset_id] = source_fingerprint
    return SharedUpstreamKey(
        stage=job.stage,
        dataset_id=dataset.dataset_id,
        population_id=population_id,
        materialization_id=materialization.identifier,
        partition_condition=job.context.partition_condition,
        seed=job.context.seed,
        seed_cohort_id=experiment.seed_cohort_id,
        training_profile_id=experiment.training_profile_id,
        training_overrides_fingerprint=compute_fingerprint(
            "campaign-training-overrides", experiment.training_overrides or {}
        ).value,
        checkpoint_profile_id=experiment.checkpoint_profile_id,
        eligibility_policy_id=experiment.eligibility_policy_id,
        readiness_gates=experiment.readiness_gates,
        score_output_name=job.outputs[0].name if job.stage is StageKind.SCORE_GENERATION else None,
        temporal_mode=materialization.split_method.value,
        source_fingerprint=source_fingerprint,
        direct_producers=(
            ()
            if job.stage is StageKind.DATASET_MATERIALIZATION
            else tuple((item.producer, item.name) for item in job.inputs)
        ),
    )
