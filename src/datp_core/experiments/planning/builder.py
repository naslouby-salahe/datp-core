"""ExperimentPlanBuilder — consolidated planning authority for DATP execution graphs.

Phase 5 of the DATP-Core simplification roadmap.  Replaces ``expand_experiment_jobs``
and ``expand_campaign_jobs`` with a single typed builder that consumes ``CompiledExperiment``
and ``ExperimentPaths``.

Every public method produces a deterministic, acyclic ``PlanningGraph`` with exact
semantic file paths, typed contexts, and explicit dependency edges.  The builder is
the sole planning authority for the DATP execution pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from itertools import product
from typing import TYPE_CHECKING

from datp_core.config.fingerprinting.canonical import compute_fingerprint
from datp_core.data.contracts.enums import ClientConstructionMethod, SplitMethod
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint
from datp_core.evaluation.enums import MissingThresholdPolicy
from datp_core.experiments.catalogue.evaluations import RecalibrationMode
from datp_core.experiments.catalogue.models import EvidenceRole
from datp_core.experiments.catalogue.sweeps import ConditionSweepRecord
from datp_core.experiments.planning.compilation import CompiledExperiment
from datp_core.experiments.planning.paths import ExperimentPaths
from datp_core.experiments.planning.sweeps import (
    _evaluation_sweep_values,
    _feature_sweep_values,
    _sweep_reference,
    _sweep_values,
)
from datp_core.learning.contracts.enums import TrainingAlgorithm
from datp_core.learning.contracts.training import DittoTrainingProfile
from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.context import (
    AnalysisContext,
    DataContext,
    EvaluationContext,
    TrainingContext,
)
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput, StageJob, StageOutput

if TYPE_CHECKING:
    from datp_core.analysis.contracts import PrerequisiteExperimentResult


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def _segment(value: object | None, *, fallback: str) -> str:
    text = fallback if value is None else str(value)
    if not _SAFE_SEGMENT.fullmatch(text):
        raise ValueError(f"Unsafe semantic output path component: {text!r}")
    return text


def _number(value: float | None, *, name: str) -> str | None:
    return None if value is None else f"{name}-{value:.17g}"


def cell_directory(context: DataContext | TrainingContext | EvaluationContext) -> str:
    parts = [
        f"population-{_segment(context.population_id, fallback='experiment')}",
        f"condition-{_segment(context.partition_condition, fallback='default')}",
        f"seed-{_segment(context.seed, fallback='aggregate')}",
    ]
    for value in (
        _number(context.federated_proximal_mu if isinstance(context, TrainingContext) else None, name="mu"),
        _number(context.ditto_proximal_weight if isinstance(context, TrainingContext) else None, name="ditto-weight"),
    ):
        if value is not None:
            parts.append(value)
    return "/".join(parts)


def evaluation_directory(context: EvaluationContext) -> str:
    parts = [
        f"evaluation-{_segment(context.evaluation_label, fallback='default')}",
        f"policy-{_segment(context.threshold_policy_id, fallback='unknown_policy')}",
        cell_directory(context),
    ]
    for value in (
        _number(context.threshold_quantile, name="quantile"),
        _number(context.shrinkage_weight, name="shrinkage"),
        _number(context.federated_summary_fixed_k, name="fixed-k"),
    ):
        if value is not None:
            parts.append(value)
    if context.fingerprint_features is not None:
        parts.append("features-" + "+".join(_segment(item, fallback="none") for item in context.fingerprint_features))
    if context.calibration_sample_count is not None:
        parts.append(f"calibration-n-{context.calibration_sample_count}-rep-{context.calibration_replicate}")
    if context.recalibration_mode is not None:
        parts.append(f"recalibration-{_segment(context.recalibration_mode, fallback='none')}")
    return "/".join(parts)


def output(name: str, relative_path: str) -> StageOutput:
    return StageOutput(name=name, relative_path=relative_path)


def shared_output_path(*, directory: str, ordinal: int, output_name: str, source_path: str) -> str:
    suffix = source_path.rsplit(".", maxsplit=1)
    extension = f".{suffix[1]}" if len(suffix) == 2 else ""
    return f"shared/{directory}/{ordinal:04d}/{output_name}{extension}"


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


class ExperimentPlanBuilder:
    """Build deterministic planning graphs from compiled experiments.

    Encapsulates all stage job creation, sweep expansion, shared-stage
    deduplication, and prerequisite wiring.  Instances hold no mutable
    planning state between ``build`` / ``build_campaign`` calls.
    """

    def __init__(self, paths: ExperimentPaths) -> None:
        self._paths = paths

    def build(
        self,
        compiled: CompiledExperiment,
        *,
        prerequisite_results: tuple[PrerequisiteExperimentResult, ...] = (),
    ) -> PlanningGraph:
        """Build a full planning graph for one compiled experiment.

        The graph contains every stage from preflight through report
        generation, with all sweep dimensions expanded and correctly
        ordered dependencies.
        """
        experiment = compiled.record
        jobs: list[StageJob] = []
        experiment_ctx = DataContext(experiment_id=experiment.identifier)

        # Preflight ---------------------------------------------------------------
        preflight = self._job(
            stage=StageKind.PREFLIGHT,
            context=experiment_ctx,
            role="resolved-configuration",
            outputs=(output("resolved_configuration", "preflight/resolved-configuration.json"),),
        )
        jobs.append(preflight)

        # Sweep expansion ---------------------------------------------------------
        conditions = tuple(
            condition.name
            for sweep in experiment.sweeps
            if isinstance(sweep, ConditionSweepRecord)
            for condition in sweep.conditions
        ) or (None,)
        mu_sweep_name = _sweep_reference(experiment.training_overrides, "mu")
        mus = _sweep_values(experiment, mu_sweep_name) or (None,)
        training_profile = compiled.training_profile
        ditto_weights = (
            training_profile.personalization_weights or (None,)
            if isinstance(training_profile, DittoTrainingProfile)
            else (None,)
        )

        # Training cells ----------------------------------------------------------
        training_jobs, training_cells = self._create_training_cells(compiled, preflight, conditions, mus, ditto_weights)
        jobs.extend(training_jobs)

        # Checkpoint selection ----------------------------------------------------
        selection = self._create_selection_stage(compiled, experiment_ctx, training_cells)
        if selection is not None:
            jobs.append(selection)

        # Scoring and calibration -------------------------------------------------
        scoring_jobs, calibration_cells_by_training, score_cells = self._create_scoring_and_calibration_cells(
            compiled, training_cells, selection
        )
        jobs.extend(scoring_jobs)

        # Evaluation ---------------------------------------------------------------
        eval_jobs_all, evaluation_jobs = self._create_evaluation_jobs(
            compiled, score_cells, calibration_cells_by_training
        )
        jobs.extend(eval_jobs_all)

        # Statistical analysis ----------------------------------------------------
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
        statistics = self._job(
            stage=StageKind.STATISTICAL_ANALYSIS,
            context=AnalysisContext(
                experiment_id=experiment.identifier,
                prerequisite_results=prerequisite_results,
            ),
            role="statistics",
            inputs=tuple(statistics_inputs),
            outputs=(output("statistical_result", "analysis/statistical-result.json"),),
            dependencies=tuple(statistics_dependencies),
        )
        jobs.append(statistics)

        # Result freeze and report ------------------------------------------------
        freeze_inputs = [self._input("statistical_result", statistics, "statistical_result")]
        freeze_inputs.extend(
            self._input(f"client_metrics_{index}", metrics, "client_metrics")
            for index, metrics in enumerate(evaluation_jobs)
        )
        result_freeze = self._job(
            stage=StageKind.RESULT_FREEZE,
            context=experiment_ctx,
            role="frozen-result",
            inputs=tuple(freeze_inputs),
            outputs=(output("frozen_result", "frozen-result.json"),),
            dependencies=(statistics.node_key, *(metrics.node_key for metrics in evaluation_jobs)),
        )
        jobs.append(result_freeze)
        report = self._job(
            stage=StageKind.REPORT_GENERATION,
            context=experiment_ctx,
            role="report",
            inputs=(self._input("frozen_result", result_freeze, "frozen_result"),),
            outputs=(output("report", "reports/report.md"),),
            dependencies=(result_freeze.node_key,),
        )
        jobs.append(report)

        graph = PlanningGraph(tuple(jobs))
        validate_acyclic(graph)
        return graph

    def build_campaign(
        self,
        compiled_experiments: tuple[CompiledExperiment, ...],
    ) -> PlanningGraph:
        """Build one active-campaign DAG across multiple compiled experiments.

        Shareable stages (materialization, training, checkpoint selection,
        score generation) are deduplicated when their upstream coordinates
        match exactly.  Non-shareable stages are kept per-experiment.
        Statistical analysis jobs receive prerequisite frozen-result inputs.
        """
        compiled_by_id = {c.record.identifier: c for c in compiled_experiments}
        source_fingerprints: dict[object, str] = {}
        shared_producers: dict[SharedUpstreamKey, StageJob] = {}
        rewritten_jobs: list[StageJob] = []
        output_paths: dict[tuple[GraphNodeKey, str], str] = {}
        node_keys: dict[GraphNodeKey, GraphNodeKey] = {}
        shared_ordinal = 0

        for compiled in compiled_experiments:
            graph = self.build(compiled)
            for job in graph.jobs:
                # Remap inputs and dependencies to previously seen producers ------
                inputs = tuple(
                    replace(
                        item,
                        producer=node_keys.get(item.producer, item.producer),
                        relative_path=output_paths.get((item.producer, item.name), item.relative_path),
                    )
                    for item in job.inputs
                )
                dependencies = tuple(dict.fromkeys(node_keys.get(item, item) for item in job.dependencies))
                candidate = replace(job, inputs=inputs, dependencies=dependencies)

                # Non-shareable stages pass through --------------------------------
                if candidate.stage not in _SHAREABLE_STAGES:
                    rewritten_jobs.append(candidate)
                    node_keys[job.node_key] = candidate.node_key
                    for stage_output in candidate.outputs:
                        output_paths[(job.node_key, stage_output.name)] = stage_output.relative_path
                    continue

                # Deduplicate shareable stages ------------------------------------
                key = self._shared_upstream_key(candidate, compiled, source_fingerprints)
                producer = shared_producers.get(key)
                if producer is not None:
                    node_keys[job.node_key] = producer.node_key
                    for stage_output in producer.outputs:
                        output_paths[(job.node_key, stage_output.name)] = stage_output.relative_path
                    continue

                # First occurrence of this shared stage ---------------------------
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

        # Prerequisite wiring for statistical analysis jobs -----------------------
        freeze_jobs = {job.context.experiment_id: job for job in rewritten_jobs if job.stage is StageKind.RESULT_FREEZE}
        campaign_jobs: list[StageJob] = []
        for job in rewritten_jobs:
            compiled = compiled_by_id.get(job.context.experiment_id)
            if job.stage is not StageKind.STATISTICAL_ANALYSIS or compiled is None or not compiled.record.prerequisites:
                campaign_jobs.append(job)
                continue
            prerequisite_inputs: list[StageInput] = []
            prerequisite_dependencies: list[GraphNodeKey] = []
            for prerequisite in compiled.record.prerequisites:
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

    @staticmethod
    def _value(value: object | None) -> str:
        return "-" if value is None else str(value)

    @staticmethod
    def _node_key(
        stage: StageKind,
        context: DataContext | TrainingContext | EvaluationContext | AnalysisContext,
        role: str,
    ) -> GraphNodeKey:
        coordinates = (
            context.experiment_id,
            context.seed if isinstance(context, DataContext) else None,
            context.population_id if isinstance(context, DataContext) else None,
            context.partition_condition if isinstance(context, DataContext) else None,
            context.federated_proximal_mu if isinstance(context, TrainingContext) else None,
            context.ditto_proximal_weight if isinstance(context, TrainingContext) else None,
            context.evaluation_label if isinstance(context, EvaluationContext) else None,
            context.threshold_policy_id if isinstance(context, EvaluationContext) else None,
            context.threshold_quantile if isinstance(context, EvaluationContext) else None,
            context.shrinkage_weight if isinstance(context, EvaluationContext) else None,
            context.federated_summary_fixed_k if isinstance(context, EvaluationContext) else None,
            context.fingerprint_features if isinstance(context, EvaluationContext) else None,
            context.calibration_sample_count if isinstance(context, EvaluationContext) else None,
            context.calibration_replicate if isinstance(context, EvaluationContext) else None,
            context.recalibration_mode if isinstance(context, EvaluationContext) else None,
        )
        return GraphNodeKey(
            label="|".join((stage.value, role, *(ExperimentPlanBuilder._value(v) for v in coordinates)))
        )

    @staticmethod
    def _input(name: str, job: StageJob, output_name: str) -> StageInput:
        return StageInput(name=name, relative_path=job.output_path(output_name), producer=job.node_key)

    def _job(
        self,
        *,
        stage: StageKind,
        context: DataContext | TrainingContext | EvaluationContext | AnalysisContext,
        role: str,
        inputs: tuple[StageInput, ...] = (),
        outputs: tuple[StageOutput, ...],
        dependencies: tuple[GraphNodeKey, ...] = (),
    ) -> StageJob:
        experiment_prefix = f"experiments/{context.experiment_id.value}/"
        return StageJob(
            node_key=self._node_key(stage, context, role),
            stage=stage,
            context=context,
            inputs=inputs,
            outputs=tuple(
                StageOutput(name=item.name, relative_path=experiment_prefix + item.relative_path) for item in outputs
            ),
            dependencies=dependencies,
        )

    @staticmethod
    def _training_outputs(
        context: DataContext | TrainingContext | EvaluationContext, *, personalized: bool
    ) -> tuple[StageOutput, ...]:
        base = f"training/{cell_directory(context)}"
        results = [
            output("checkpoint", f"{base}/checkpoint.safetensors"),
            output("selection_evidence", f"{base}/selection-evidence.json"),
        ]
        if personalized:
            results.append(output("personalized_checkpoint", f"{base}/personalized-checkpoint.safetensors"))
        return tuple(results)

    @staticmethod
    def _score_output(context: DataContext | TrainingContext | EvaluationContext, name: str) -> StageOutput:
        return output(name, f"scores/{cell_directory(context)}/{name.replace('_', '-')}.parquet")

    def _create_training_cells(
        self,
        compiled: CompiledExperiment,
        preflight: StageJob,
        conditions: tuple[str | None, ...],
        mus: tuple[float | None, ...],
        ditto_weights: tuple[float | None, ...],
    ) -> tuple[list[StageJob], list[tuple[TrainingContext, StageJob, StageJob]]]:
        experiment = compiled.record
        population_by_id = {p.identifier: p for p in compiled.populations}
        jobs: list[StageJob] = []
        training_cells: list[tuple[TrainingContext, StageJob, StageJob]] = []
        for seed, condition, population_id in product(
            compiled.seed_cohort.training_seeds, conditions, experiment.population_ids
        ):
            materialization_ctx = DataContext(
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
            population = population_by_id.get(population_id)
            if population is None:
                raise ValueError(f"Population '{population_id}' not found in compiled experiment")
            dataset = compiled.datasets.get(population.dataset_id)
            if dataset is None:
                raise ValueError(f"Dataset '{population.dataset_id}' not found in compiled experiment")
            setup = dataset.setup(population.setup_id)
            if setup.client_construction.method is ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS:
                materialization_outputs.append(
                    output("partition_manifest", f"{materialization_base}/partition-manifest.json")
                )
            materialization = self._job(
                stage=StageKind.DATASET_MATERIALIZATION,
                context=materialization_ctx,
                role="materialization",
                inputs=(self._input("resolved_configuration", preflight, "resolved_configuration"),),
                outputs=tuple(materialization_outputs),
                dependencies=(preflight.node_key,),
            )
            jobs.append(materialization)

            for proximal_mu, ditto_weight in product(mus, ditto_weights):
                seed_ctx = TrainingContext(
                    experiment_id=experiment.identifier,
                    seed=int(seed.value),
                    partition_condition=condition,
                    population_id=population_id,
                    federated_proximal_mu=proximal_mu,
                    ditto_proximal_weight=ditto_weight,
                )
                training = self._job(
                    stage=StageKind.MODEL_TRAINING,
                    context=seed_ctx,
                    role="training",
                    inputs=(self._input("materialization", materialization, "dataset"),),
                    outputs=self._training_outputs(
                        seed_ctx,
                        personalized=isinstance(compiled.training_profile, DittoTrainingProfile),
                    ),
                    dependencies=(materialization.node_key,),
                )
                jobs.append(training)
                training_cells.append((seed_ctx, materialization, training))
        return jobs, training_cells

    def _create_selection_stage(
        self,
        compiled: CompiledExperiment,
        experiment_ctx: DataContext,
        training_cells: list[tuple[TrainingContext, StageJob, StageJob]],
    ) -> StageJob | None:
        experiment = compiled.record
        training_profile = compiled.training_profile
        role: str | None
        if (
            experiment.evidence_role is EvidenceRole.CONFIRMATORY
            and compiled.checkpoint_profile.selection.kind == "authorized_lookup"
        ):
            role = "cohort"
        elif training_profile.algorithm is TrainingAlgorithm.FEDPROX:
            role = "fedprox"
        elif (
            isinstance(training_profile, DittoTrainingProfile)
            and experiment.personalization_parameter_selection_source is None
        ):
            role = "ditto"
        else:
            return None

        inputs: list[StageInput] = []
        for index, (_, _, training) in enumerate(training_cells):
            inputs.extend(
                (
                    self._input(f"checkpoint_{index}", training, "checkpoint"),
                    self._input(f"selection_evidence_{index}", training, "selection_evidence"),
                )
            )
        return self._job(
            stage=StageKind.CHECKPOINT_SELECTION,
            context=experiment_ctx,
            role=role,
            inputs=tuple(inputs),
            outputs=(output("checkpoint_selection", f"checkpoint-selection/{role}.json"),),
            dependencies=tuple(training.node_key for _, _, training in training_cells),
        )

    def _create_scoring_and_calibration_cells(
        self,
        compiled: CompiledExperiment,
        training_cells: list[tuple[TrainingContext, StageJob, StageJob]],
        selection: StageJob | None,
    ) -> tuple[
        list[StageJob],
        dict[tuple[object, ...], list[tuple[TrainingContext | EvaluationContext, StageJob, str]]],
        dict[tuple[object, ...], tuple[TrainingContext, StageJob, StageJob, StageJob | None]],
    ]:
        experiment = compiled.record
        population_by_id = {p.identifier: p for p in compiled.populations}
        jobs: list[StageJob] = []
        calibration_cells_by_training: dict[
            tuple[object, ...], list[tuple[TrainingContext | EvaluationContext, StageJob, str]]
        ] = {}
        score_cells: dict[tuple[object, ...], tuple[TrainingContext, StageJob, StageJob, StageJob | None]] = {}
        for seed_ctx, materialization, training in training_cells:
            scoring_inputs = [
                self._input("checkpoint", training, "checkpoint"),
                self._input("materialization", materialization, "dataset"),
                self._input("selection_evidence", training, "selection_evidence"),
            ]
            if any(item.name == "personalized_checkpoint" for item in training.outputs):
                scoring_inputs.append(self._input("personalized_checkpoint", training, "personalized_checkpoint"))
            dependencies = [training.node_key, materialization.node_key]
            if selection is not None:
                scoring_inputs.append(self._input("checkpoint_selection", selection, "checkpoint_selection"))
                dependencies.append(selection.node_key)

            calibration = self._job(
                stage=StageKind.SCORE_GENERATION,
                context=seed_ctx,
                role="calibration-scores",
                inputs=tuple(scoring_inputs),
                outputs=(self._score_output(seed_ctx, "calibration_scores"),),
                dependencies=tuple(dependencies),
            )
            test = self._job(
                stage=StageKind.SCORE_GENERATION,
                context=seed_ctx,
                role="test-scores",
                inputs=tuple(scoring_inputs),
                outputs=(self._score_output(seed_ctx, "test_scores"),),
                dependencies=tuple(dependencies),
            )
            jobs.extend((calibration, test))

            calibration_cells: list[tuple[TrainingContext | EvaluationContext, StageJob, str]] = [
                (seed_ctx, calibration, "calibration_scores")
            ]
            if experiment.calibration_subset is not None:
                requested_sweep = experiment.calibration_subset.requested_sample_count.get("from_sweep")
                requested_counts = _sweep_values(experiment, requested_sweep)
                if not requested_counts or any(not value.is_integer() or value < 1.0 for value in requested_counts):
                    raise ValueError("Calibration subset requires a positive integer sample-count sweep")
                for requested_count, replicate in product(
                    (int(value) for value in requested_counts),
                    range(experiment.calibration_subset.replicate_count.value),
                ):
                    subset_ctx = EvaluationContext(
                        experiment_id=seed_ctx.experiment_id,
                        seed=seed_ctx.seed,
                        partition_condition=seed_ctx.partition_condition,
                        population_id=seed_ctx.population_id,
                        federated_proximal_mu=seed_ctx.federated_proximal_mu,
                        ditto_proximal_weight=seed_ctx.ditto_proximal_weight,
                        calibration_sample_count=requested_count,
                        calibration_replicate=replicate,
                        threshold_policy_id=experiment.evaluations[0].threshold_policy_id,
                        missing_threshold_policy=MissingThresholdPolicy.FAIL,
                    )
                    subset = self._job(
                        stage=StageKind.CALIBRATION_SUBSAMPLING,
                        context=subset_ctx,
                        role="calibration-subset",
                        inputs=(self._input("calibration_scores", calibration, "calibration_scores"),),
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
            population = population_by_id.get(seed_ctx.population_id)
            if population is None:
                raise ValueError(f"Population '{seed_ctx.population_id}' not found in compiled experiment")
            dataset = compiled.datasets.get(population.dataset_id)
            if dataset is None:
                raise ValueError(f"Dataset '{population.dataset_id}' not found in compiled experiment")
            setup = dataset.setup(population.setup_id)
            materialization_contract = next(
                item for item in dataset.materializations if item.identifier == setup.materialization_id
            )
            if materialization_contract.split_method is SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL:
                future = self._job(
                    stage=StageKind.SCORE_GENERATION,
                    context=seed_ctx,
                    role="future-recalibration-scores",
                    inputs=tuple(scoring_inputs),
                    outputs=(self._score_output(seed_ctx, "future_recalibration_scores"),),
                    dependencies=tuple(dependencies),
                )
                jobs.append(future)
            calibration_cells_by_training[key] = calibration_cells
            score_cells[key] = (seed_ctx, test, calibration, future)
        return jobs, calibration_cells_by_training, score_cells

    def _create_evaluation_jobs(
        self,
        compiled: CompiledExperiment,
        score_cells: dict[tuple[object, ...], tuple[TrainingContext, StageJob, StageJob, StageJob | None]],
        calibration_cells_by_training: dict[
            tuple[object, ...], list[tuple[TrainingContext | EvaluationContext, StageJob, str]]
        ],
    ) -> tuple[list[StageJob], list[StageJob]]:
        experiment = compiled.record
        jobs: list[StageJob] = []
        evaluation_jobs: list[StageJob] = []
        compiled_eval_by_label = {e.record.label: e for e in compiled.evaluations}
        for key, (seed_ctx, test, _, future) in score_cells.items():
            for evaluation in experiment.evaluations:
                population_id = (
                    evaluation.population_id or compiled_eval_by_label[evaluation.label].population.identifier
                )
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
                        evaluation_ctx = EvaluationContext(
                            experiment_id=experiment.identifier,
                            seed=seed_ctx.seed,
                            partition_condition=seed_ctx.partition_condition,
                            federated_proximal_mu=seed_ctx.federated_proximal_mu,
                            ditto_proximal_weight=seed_ctx.ditto_proximal_weight,
                            calibration_sample_count=calibration_ctx.calibration_sample_count
                            if isinstance(calibration_ctx, EvaluationContext)
                            else None,
                            calibration_replicate=calibration_ctx.calibration_replicate
                            if isinstance(calibration_ctx, EvaluationContext)
                            else None,
                            threshold_quantile=quantile,
                            shrinkage_weight=shrinkage,
                            federated_summary_fixed_k=fixed_k,
                            fingerprint_features=features,
                            evaluation_label=evaluation.label,
                            population_id=population_id,
                            recalibration_mode=evaluation.recalibration_mode,
                            threshold_policy_id=evaluation.threshold_policy_id,
                            missing_threshold_policy=MissingThresholdPolicy.FAIL,
                        )
                        evaluation_base = evaluation_directory(evaluation_ctx)
                        threshold = self._job(
                            stage=StageKind.THRESHOLD_CONSTRUCTION,
                            context=evaluation_ctx,
                            role="thresholds",
                            inputs=(self._input(calibration_output, calibration_job, calibration_output),),
                            outputs=(
                                output("thresholds", f"thresholds/{evaluation_base}/thresholds.parquet"),
                                output("diagnostics", f"thresholds/{evaluation_base}/diagnostics.json"),
                            ),
                            dependencies=(calibration_job.node_key,),
                        )
                        metrics = self._job(
                            stage=StageKind.OPERATING_POINT_EVALUATION,
                            context=evaluation_ctx,
                            role="metrics",
                            inputs=(
                                self._input("thresholds", threshold, "thresholds"),
                                self._input("test_scores", test, "test_scores"),
                            ),
                            outputs=(
                                output("client_metrics", f"evaluations/{evaluation_base}/client-metrics.parquet"),
                            ),
                            dependencies=(threshold.node_key, test.node_key),
                        )
                        jobs.extend((threshold, metrics))
                        evaluation_jobs.append(metrics)
        return jobs, evaluation_jobs

    @staticmethod
    def _shared_upstream_key(
        job: StageJob,
        compiled: CompiledExperiment,
        source_fingerprints: dict[object, str],
    ) -> SharedUpstreamKey:
        """Build a structural key that determines whether two campaign jobs share."""
        experiment = compiled.record
        population_id = job.context.population_id if isinstance(job.context, DataContext) else None
        if population_id is None:
            if not compiled.populations:
                raise ValueError(f"Experiment '{experiment.identifier.value}' has no resolved populations")
            population_id = compiled.populations[0].identifier
        population = next((p for p in compiled.populations if p.identifier == population_id), None)
        if population is None:
            raise ValueError(f"Population '{population_id}' not found in compiled experiment")
        dataset = compiled.datasets.get(population.dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset '{population.dataset_id}' not found in compiled experiment")
        setup = dataset.setup(population.setup_id)
        materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)
        source_fingerprint = source_fingerprints.get(dataset.dataset_id)
        if source_fingerprint is None:
            from datp_core.core.registry import TypedDomainRegistry

            registry = TypedDomainRegistry(dict(compiled.datasets))
            source_fingerprint = compute_experiment_source_fingerprint(
                datasets=registry, dataset_ids=(dataset.dataset_id,)
            ).value
            source_fingerprints[dataset.dataset_id] = source_fingerprint
        return SharedUpstreamKey(
            stage=job.stage,
            dataset_id=dataset.dataset_id,
            population_id=population_id,
            materialization_id=materialization.identifier,
            partition_condition=(job.context.partition_condition if isinstance(job.context, DataContext) else None),
            seed=job.context.seed if isinstance(job.context, DataContext) else None,
            seed_cohort_id=experiment.seed_cohort_id,
            training_profile_id=experiment.training_profile_id,
            training_overrides_fingerprint=compute_fingerprint(
                "campaign-training-overrides", experiment.training_overrides or {}
            ).value,
            checkpoint_profile_id=experiment.checkpoint_profile_id,
            eligibility_policy_id=experiment.eligibility_policy_id,
            readiness_gates=experiment.readiness_gates,
            score_output_name=next((o.name for o in job.outputs), None)
            if job.stage is StageKind.SCORE_GENERATION
            else None,
            temporal_mode=materialization.split_method.value,
            source_fingerprint=source_fingerprint,
            direct_producers=(
                ()
                if job.stage is StageKind.DATASET_MATERIALIZATION
                else tuple((item.producer, item.name) for item in job.inputs)
            ),
        )


@dataclass(frozen=True)
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
