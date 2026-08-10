"""Deterministic stage execution over already-planned experiment coordinates."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from shutil import rmtree

from datp_core.analysis.metrics.federated_publication import EvaluateFederatedDetectorResult
from datp_core.analysis.metrics.models import metric_by_id
from datp_core.artifacts.layout import experiment_output_directory
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ExperimentId, StageExecutionEvidence
from datp_core.data.service import DatasetMaterializationRequest, materialize_datasets
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest
from datp_core.detector.training.federated_publication import TrainFederatedDetectorResult
from datp_core.experiments.common.coordinates import ExecutionRoute, ExperimentCoordinate, execution_route_for
from datp_core.experiments.execution.context import FederatedExecutionContext
from datp_core.experiments.execution.models import (
    ANCHOR_REPRODUCTION_RECIPE,
    STANDARD_FEDERATED_RECIPE,
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
    directory = experiment_output_directory(output_root, coordinate)
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


def execute_campaign(
    *,
    campaign: CampaignPlan,
    stage_runner: StageRunner,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> CampaignExecution:
    total = len(campaign.entries)
    _emit_progress(progress, ProgressEvent(kind=ProgressEventKind.CAMPAIGN_BEGIN, total=total))
    experiments: list[ExperimentExecution] = []
    for entry in campaign.entries:
        _emit_progress(
            progress,
            ProgressEvent(
                kind=ProgressEventKind.COORDINATE_BEGIN,
                coordinate=entry.coordinate,
                ordinal=entry.ordinal.value,
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
                ordinal=entry.ordinal.value,
                total=total,
                outcome=StageOutcome.COMPLETED if result.successful else StageOutcome.BLOCKED,
                detail=f"stages={len(result.stages)}",
                elapsed_seconds=time.monotonic() - started,
            ),
        )
        experiments.append(result)
    _emit_progress(
        progress,
        ProgressEvent(
            kind=ProgressEventKind.CAMPAIGN_END,
            total=total,
            detail=f"experiments={len(experiments)}",
        ),
    )
    return CampaignExecution(experiments=tuple(experiments))


@dataclass
class PipelineStageRunner:
    """Execute lower-level capability stages for one coordinate at a time."""

    progress_hook: ProgressHook | None = None
    _workspace: ExperimentWorkspace | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._context_cache: dict[tuple[object, ...], FederatedExecutionContext] = {}
        self._evaluation_cache: dict[Path, EvaluateFederatedDetectorResult] = {}
        self._training_cache: dict[tuple[object, ...], TrainFederatedDetectorResult] = {}
        self._score_cache: dict[tuple[object, ...], FederatedScoreArtifactManifest] = {}

    def _workspace_for(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExperimentWorkspace:
        workspace = self._workspace
        if workspace is None or workspace.coordinate != coordinate or workspace.output_root != output_root:
            workspace = ExperimentWorkspace(
                coordinate=coordinate,
                output_root=output_root,
                progress=self.progress_hook,
                shared_context_cache=self._context_cache,
                shared_evaluation_cache=self._evaluation_cache,
                shared_training_cache=self._training_cache,
                shared_score_cache=self._score_cache,
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
                elapsed_seconds=time.monotonic() - started,
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
                return self._generate_scores(stage, coordinate, workspace)
            case PipelineStage.BUILD_CALIBRATION:
                return self._build_calibration(stage, coordinate, workspace)
            case PipelineStage.CONSTRUCT_THRESHOLDS:
                return self._construct_thresholds(stage, coordinate, workspace)
            case PipelineStage.EVALUATE_DETECTOR:
                return self._evaluate_detector(stage, coordinate, workspace)
            case PipelineStage.ANALYZE_EVIDENCE:
                return self._analyze_evidence(stage, coordinate, workspace)
            case PipelineStage.FINALIZE_PUBLICATION:
                return self._finalize_publication(stage, workspace)
        raise ScientificContractError(
            ErrorMessage(f"unsupported execution stage: {stage.value}"), subject=coordinate.experiment
        )

    def _materialize_dataset(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        result = materialize_datasets(
            DatasetMaterializationRequest(data_root=DATA_ROOT, datasets=(coordinate.dataset,), overwrite=False)
        )
        publication = result.publications[0]
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
            evidence=StageExecutionEvidence(f"rounds={len(result.training.history.rounds)}"),
        )

    def _generate_scores(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
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
        coordinate: ExperimentCoordinate,
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
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(f"threshold_method={coordinate.threshold_method.value}"),
        )

    def _evaluate_detector(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
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
        result = metric_by_id(workspace.evaluation_document().population.metrics, coordinate.metric)
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
        workspace.evaluation_document()
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence("publication written"),
        )
