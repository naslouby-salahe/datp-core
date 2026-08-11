from __future__ import annotations

import time
from _thread import LockType, allocate_lock
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from shutil import rmtree

from datp_core.analysis.metrics.models import metric_by_id
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import DatasetId, ExperimentId, StageExecutionEvidence
from datp_core.core.numeric import CampaignCoordinateCount, ElapsedSeconds, ParallelEvaluationWorkerCount
from datp_core.data.paths import canonical_root_under
from datp_core.data.service import DatasetMaterializationRequest, materialize_datasets
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.coordinates import ExecutionRoute, ExperimentCoordinate, execution_route_for
from datp_core.experiments.execution.context import training_coordinate_for
from datp_core.experiments.execution.layout import federated_training_directory
from datp_core.experiments.execution.models import (
    ANCHOR_REPRODUCTION_RECIPE,
    STANDARD_FEDERATED_RECIPE,
    CampaignEntry,
    CampaignExecution,
    CampaignPlan,
    ExecutionRecipe,
    ExperimentExecution,
    PipelineStage,
    ProgressEvent,
    ProgressEventKind,
    ProgressHook,
    StageExecution,
    StageOutcome,
    StageRunner,
)
from datp_core.experiments.execution.workspace import ExperimentWorkspace
from datp_core.runtime.configuration import DATA_ROOT

MAXIMUM_PARALLEL_THRESHOLD_EVALUATIONS = ParallelEvaluationWorkerCount(5)


def _empty_dataset_ids() -> set[DatasetId]:
    return set()


def resolve_execution_recipe(coordinate: ExperimentCoordinate) -> ExecutionRecipe:
    route = execution_route_for(coordinate)
    if route is not ExecutionRoute.SINGLE_COORDINATE:
        raise ScientificContractError(
            ErrorMessage(f"{route.value} coordinates require their dedicated joint experiment execution route"),
            subject=coordinate.experiment,
        )
    if coordinate.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return ANCHOR_REPRODUCTION_RECIPE
    return STANDARD_FEDERATED_RECIPE


def execute_experiment(
    *,
    coordinate: ExperimentCoordinate,
    stage_runner: StageRunner,
    output_root: Path,
    overwrite: bool,
) -> ExperimentExecution:
    recipe = resolve_execution_recipe(coordinate)
    directory = evaluation_run_directory(output_root, coordinate)
    if directory.exists():
        if not overwrite:
            raise FileExistsError(f"experiment output already exists: {directory}")
        rmtree(directory)

    executions: list[StageExecution] = []
    for stage in recipe.stages:
        result = stage_runner.run(stage, coordinate, output_root)
        if result.stage is not stage:
            raise ValueError("stage runner returned a result for the wrong stage")
        executions.append(result)
        if result.outcome in {StageOutcome.BLOCKED, StageOutcome.FAILED}:
            break
    return ExperimentExecution(coordinate=coordinate, recipe=recipe, stages=tuple(executions))


def _emit_progress(progress: ProgressHook | None, event: ProgressEvent) -> None:
    if progress is not None:
        progress.emit(event)


@dataclass(kw_only=True)
class _SerializedProgressHook:
    delegate: ProgressHook
    _lock: LockType = field(default_factory=allocate_lock, init=False, repr=False)

    def emit(self, event: ProgressEvent) -> None:
        with self._lock:
            self.delegate.emit(event)


def _execute_campaign_entry(
    *,
    entry: CampaignEntry,
    total: CampaignCoordinateCount,
    stage_runner: StageRunner,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None,
) -> ExperimentExecution:
    _emit_progress(
        progress,
        ProgressEvent(
            kind=ProgressEventKind.COORDINATE_BEGIN,
            coordinate=entry.coordinate,
            ordinal=entry.ordinal,
            total=total,
        ),
    )
    started = time.monotonic()
    result = execute_experiment(
        coordinate=entry.coordinate,
        stage_runner=stage_runner,
        output_root=output_root,
        overwrite=overwrite,
    )
    _emit_progress(
        progress,
        ProgressEvent(
            kind=ProgressEventKind.COORDINATE_END,
            coordinate=entry.coordinate,
            ordinal=entry.ordinal,
            total=total,
            outcome=StageOutcome.COMPLETED if result.successful else StageOutcome.BLOCKED,
            detail=StageExecutionEvidence(f"stages={len(result.stages)}"),
            elapsed_seconds=ElapsedSeconds(time.monotonic() - started),
        ),
    )
    return result


def _training_coordinate_batches(campaign: CampaignPlan) -> tuple[tuple[CampaignEntry, ...], ...]:
    batches: dict[FederatedTrainingCoordinate, list[CampaignEntry]] = {}
    for entry in campaign.entries:
        training_coordinate = training_coordinate_for(entry.coordinate)
        batches.setdefault(training_coordinate, []).append(entry)
    return tuple(tuple(batch) for batch in batches.values())


def _can_parallelize_threshold_evaluations(
    batch: tuple[CampaignEntry, ...],
    stage_runner: StageRunner,
) -> bool:
    return (
        len(batch) > 1
        and isinstance(stage_runner, PipelineStageRunner)
        and batch[0].coordinate.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
    )


def execute_campaign(
    *,
    campaign: CampaignPlan,
    stage_runner: StageRunner,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> CampaignExecution:
    if overwrite:
        _remove_rebuilt_training_artifacts(campaign, output_root)
    total = CampaignCoordinateCount(len(campaign.entries))
    synchronized_progress = _SerializedProgressHook(delegate=progress) if progress is not None else None
    _emit_progress(synchronized_progress, ProgressEvent(kind=ProgressEventKind.CAMPAIGN_BEGIN, total=total))
    experiments: list[ExperimentExecution] = []
    for batch in _training_coordinate_batches(campaign):
        first, *remaining = batch
        first_result = _execute_campaign_entry(
            entry=first,
            total=total,
            stage_runner=stage_runner,
            output_root=output_root,
            overwrite=overwrite,
            progress=synchronized_progress,
        )
        experiments.append(first_result)
        if (
            not remaining
            or not first_result.successful
            or not _can_parallelize_threshold_evaluations(batch, stage_runner)
        ):
            for entry in remaining:
                experiments.append(
                    _execute_campaign_entry(
                        entry=entry,
                        total=total,
                        stage_runner=stage_runner,
                        output_root=output_root,
                        overwrite=overwrite,
                        progress=synchronized_progress,
                    )
                )
            if isinstance(stage_runner, PipelineStageRunner):
                stage_runner.release_completed_training_coordinate()
            continue
        if not isinstance(stage_runner, PipelineStageRunner):
            raise AssertionError("parallel threshold evaluation requires a pipeline stage runner")
        runners = tuple(stage_runner.with_fixed_evidence(progress=synchronized_progress) for _ in remaining)
        worker_count = min(MAXIMUM_PARALLEL_THRESHOLD_EVALUATIONS.value, len(remaining))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = tuple(
                executor.submit(
                    _execute_campaign_entry,
                    entry=entry,
                    total=total,
                    stage_runner=runner,
                    output_root=output_root,
                    overwrite=overwrite,
                    progress=synchronized_progress,
                )
                for entry, runner in zip(remaining, runners, strict=True)
            )
            experiments.extend(future.result() for future in futures)
        stage_runner.release_completed_training_coordinate()
    _emit_progress(
        synchronized_progress,
        ProgressEvent(
            kind=ProgressEventKind.CAMPAIGN_END,
            total=total,
            detail=StageExecutionEvidence(f"experiments={len(experiments)}"),
        ),
    )
    ordinal_by_coordinate = {entry.coordinate.stable_key: entry.ordinal.value for entry in campaign.entries}
    ordered_experiments = tuple(sorted(experiments, key=lambda item: ordinal_by_coordinate[item.coordinate.stable_key]))
    return CampaignExecution(experiments=ordered_experiments)


def _remove_rebuilt_training_artifacts(campaign: CampaignPlan, output_root: Path) -> None:
    directories = {
        federated_training_directory(training_coordinate_for(entry.coordinate), output_root)
        for entry in campaign.entries
    }
    for directory in directories:
        if directory.exists():
            rmtree(directory)


@dataclass
class PipelineStageRunner:
    progress_hook: ProgressHook | None = None
    _workspace: ExperimentWorkspace | None = None
    _materialized_datasets: set[DatasetId] = field(default_factory=_empty_dataset_ids, init=False, repr=False)
    _fixed_score_workspaces: dict[tuple[FederatedTrainingCoordinate, Path], ExperimentWorkspace] = field(
        default_factory=dict[tuple[FederatedTrainingCoordinate, Path], ExperimentWorkspace],
        init=False,
        repr=False,
    )

    def with_fixed_evidence(self, *, progress: ProgressHook | None) -> PipelineStageRunner:
        fixed_workspace = self._workspace
        if fixed_workspace is None:
            raise ValueError("fixed evidence requires a prepared pipeline workspace")
        key = (training_coordinate_for(fixed_workspace.coordinate), fixed_workspace.output_root)
        runner = PipelineStageRunner(progress_hook=progress)
        runner._fixed_score_workspaces[key] = fixed_workspace
        return runner

    def release_completed_training_coordinate(self) -> None:
        self._workspace = None
        self._fixed_score_workspaces.clear()

    def _workspace_for(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExperimentWorkspace:
        workspace = self._workspace
        if workspace is None or workspace.coordinate != coordinate or workspace.output_root != output_root:
            key = (training_coordinate_for(coordinate), output_root)
            fixed_workspace = self._fixed_score_workspaces.get(key)
            if fixed_workspace is None:
                workspace = ExperimentWorkspace(
                    coordinate=coordinate,
                    output_root=output_root,
                    progress=self.progress_hook,
                )
                self._fixed_score_workspaces[key] = workspace
            else:
                workspace = ExperimentWorkspace(
                    coordinate=coordinate,
                    output_root=output_root,
                    progress=self.progress_hook,
                    fixed_context=fixed_workspace.context,
                    fixed_training=fixed_workspace.training,
                    fixed_scores=fixed_workspace.scores,
                )
            self._workspace = workspace
        return workspace

    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        output_root: Path,
    ) -> StageExecution:
        _emit_progress(
            self.progress_hook,
            ProgressEvent(kind=ProgressEventKind.STAGE_BEGIN, coordinate=coordinate, stage=stage),
        )
        started = time.monotonic()
        try:
            execution = self._run(stage, coordinate, output_root)
        except ScientificContractError as error:
            execution = StageExecution(
                stage=stage,
                outcome=StageOutcome.BLOCKED,
                evidence=StageExecutionEvidence(str(error)),
            )
        _emit_progress(
            self.progress_hook,
            ProgressEvent(
                kind=ProgressEventKind.STAGE_END,
                coordinate=coordinate,
                stage=stage,
                outcome=execution.outcome,
                elapsed_seconds=ElapsedSeconds(time.monotonic() - started),
                detail=execution.evidence,
            ),
        )
        return execution

    def _run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        output_root: Path,
    ) -> StageExecution:
        if coordinate.temporal_state is not None:
            raise ScientificContractError(
                ErrorMessage("temporal coordinates require the paired temporal execution route"),
                subject=coordinate.temporal_state,
            )
        workspace = self._workspace_for(coordinate, output_root)
        match stage:
            case PipelineStage.PREFLIGHT:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=StageExecutionEvidence(f"coordinate validated: {coordinate.stable_key}"),
                )
            case PipelineStage.MATERIALIZE_DATASET:
                return self._materialize_dataset(stage, coordinate)
            case PipelineStage.CONSTRUCT_POPULATION:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=StageExecutionEvidence(f"clients={len(workspace.context.clients)}"),
                )
            case PipelineStage.FIT_PREPROCESSING:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=StageExecutionEvidence(
                        f"preprocessed_clients={len(workspace.context.preprocessing.client_publications)}"
                    ),
                )
            case PipelineStage.TRAIN_DETECTOR:
                return self._train_detector(stage, workspace)
            case PipelineStage.GENERATE_SCORES:
                return self._generate_scores(stage, workspace)
            case PipelineStage.BUILD_CALIBRATION:
                return self._build_calibration(stage, workspace)
            case PipelineStage.CONSTRUCT_THRESHOLDS:
                return self._construct_thresholds(stage, coordinate)
            case PipelineStage.EVALUATE_DETECTOR:
                return self._evaluate_detector(stage, workspace)
            case PipelineStage.ANALYZE_EVIDENCE:
                return self._analyze_evidence(stage, coordinate, workspace)
            case PipelineStage.FINALIZE_PUBLICATION:
                return self._finalize_publication(stage, workspace)
        raise ScientificContractError(
            ErrorMessage(f"unsupported execution stage: {stage.value}"), subject=coordinate.experiment
        )

    def _materialize_dataset(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        if coordinate.dataset in self._materialized_datasets:
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.COMPLETED,
                evidence=StageExecutionEvidence(f"{coordinate.dataset.value} canonical dataset reused"),
            )
        canonical_root = canonical_root_under(DATA_ROOT, coordinate.dataset)
        if (canonical_root / "dataset_manifest.json").is_file():
            self._materialized_datasets.add(coordinate.dataset)
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.COMPLETED,
                evidence=StageExecutionEvidence(f"{coordinate.dataset.value} canonical dataset reused"),
            )
        result = materialize_datasets(
            DatasetMaterializationRequest(data_root=DATA_ROOT, datasets=(coordinate.dataset,), overwrite=False)
        )
        publication = result.publications[0]
        self._materialized_datasets.add(coordinate.dataset)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(f"{publication.dataset.value} assets={len(publication.assets)}"),
        )

    def _train_detector(self, stage: PipelineStage, workspace: ExperimentWorkspace) -> StageExecution:
        result = workspace.training
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(
                f"rounds={len(result.training.history.rounds)} termination={result.training.termination_reason.value}"
            ),
        )

    def _generate_scores(
        self,
        stage: PipelineStage,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(f"scored_clients={len(workspace.scores.evaluation_records)}"),
        )

    def _build_calibration(
        self,
        stage: PipelineStage,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        eligible = workspace.eligible_calibration_scores()
        evidence = f"eligible_clients={len(eligible)}"
        if workspace.calibration is not None:
            lattice = workspace.calibration
            evidence = (
                f"{evidence} ablation_clients={len(lattice.eligible_clients)} "
                f"replicates={len(lattice.replicate_manifests)}"
            )
        return StageExecution(stage=stage, outcome=StageOutcome.COMPLETED, evidence=StageExecutionEvidence(evidence))

    def _construct_thresholds(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
    ) -> StageExecution:
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(f"threshold_method={coordinate.threshold_method.value}"),
        )

    def _evaluate_detector(
        self,
        stage: PipelineStage,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        _ = workspace.evaluation
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence("evaluation completed"),
        )

    def _analyze_evidence(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        result = metric_by_id(workspace.evaluation.population.metrics, coordinate.metric)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(f"metric={coordinate.metric.value} status={result.status.value}"),
        )

    def _finalize_publication(
        self,
        stage: PipelineStage,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        _ = workspace.evaluation
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence("publication written"),
        )
