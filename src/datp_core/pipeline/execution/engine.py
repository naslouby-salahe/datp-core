"""Recipe resolution, deterministic campaign construction, and stage sequencing.

The VERIFY_ANCHOR stage is the one narrow, deliberate exception to the services-do-not-
import-workflows direction: anchor verification is a self-contained scientific gate over
``datp_core.anchor`` with no further dependency on any other service or workflow, it applies
only to the rare historical-reproduction recipe, and importing it here creates no import
cycle (``workflows.anchor`` never imports this module).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from shutil import rmtree

from datp_core.anchor.models import VerifyAnchorStageRequest
from datp_core.domain.enums import ExperimentId, PublicationStatus
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import ByteCount, Checksum, checksum_file
from datp_core.evaluation.models import metric_by_id
from datp_core.evaluation.population import FederatedEvaluationAssetName
from datp_core.pipeline.execution.models import (
    ANCHOR_REPRODUCTION_RECIPE,
    STANDARD_FEDERATED_RECIPE,
    CampaignEntry,
    CampaignExecution,
    CampaignPlan,
    ExecutionProvenance,
    ExecutionRecipe,
    ExistingExperimentState,
    ExperimentExecution,
    ExperimentOutputStore,
    PipelineStage,
    StageExecution,
    StageOutcome,
    StageRunner,
    campaign_digest,
)
from datp_core.pipeline.execution.workspace import EvaluationRunAssetDirectory, ExperimentWorkspace
from datp_core.pipeline.planning import (
    ExecutionRoute,
    ExperimentCoordinate,
    ExperimentPlan,
    PlanDisposition,
    execution_route_for,
)
from datp_core.pipeline.preparation.datasets import MaterializeDatasetRequest, materialize_dataset
from datp_core.pipeline.publication.layout import experiment_output_directory
from datp_core.pipeline.publication.models import ArtifactKind, ArtifactRecord, ArtifactState, CompletionState
from datp_core.pipeline.publication.service import (
    build_completion_record,
    read_completion_record,
    validate_reload,
    write_completion_record,
)
from datp_core.pipeline.workflows.anchor import verify_anchor
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.graph import (
    ObservationBoundary,
    ObservationContext,
    ObservationHook,
    observe_graph_boundary,
)
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.runtime.configuration import DATA_ROOT


def resolve_execution_recipe(coordinate: ExperimentCoordinate) -> ExecutionRecipe:
    route = execution_route_for(coordinate)
    if route is not ExecutionRoute.SINGLE_COORDINATE:
        raise ScientificContractError(
            f"{route.value} coordinates execute through their dedicated joint workflow, not a single-coordinate recipe",
            subject=coordinate.experiment,
        )
    if coordinate.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return ANCHOR_REPRODUCTION_RECIPE
    return STANDARD_FEDERATED_RECIPE


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    coordinates = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.disposition is PlanDisposition.EXECUTABLE
        and execution_route_for(entry.coordinate) is ExecutionRoute.SINGLE_COORDINATE
    )
    entries = tuple(CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates))
    return CampaignPlan(
        entries=entries,
        digest=campaign_digest(entries),
        plan_digest=Checksum(plan.digest),
    )


def protocol_digest() -> Checksum:
    return canonical_checksum(EXPERIMENTS)


def execute_experiment(
    *,
    coordinate: ExperimentCoordinate,
    provenance: ExecutionProvenance,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root: Path,
    overwrite: bool = False,
) -> ExperimentExecution:
    recipe = resolve_execution_recipe(coordinate)
    existing_state = output_store.state(coordinate, output_root)
    if overwrite:
        if existing_state is not ExistingExperimentState.ABSENT:
            output_store.delete(coordinate, output_root)
    elif existing_state is ExistingExperimentState.COMPLETE_VALID:
        return ExperimentExecution(
            coordinate=coordinate,
            recipe=recipe,
            stages=(),
            reused_complete_experiment=True,
        )
    elif existing_state is ExistingExperimentState.COMPLETE_INVALID:
        raise ValueError("completed experiment failed publication validation")
    elif existing_state is ExistingExperimentState.INCOMPLETE:
        output_store.delete(coordinate, output_root)

    executions: list[StageExecution] = []
    for stage in recipe.stages:
        result = stage_runner.run(stage, coordinate, provenance, output_root)
        if result.stage is not stage:
            raise ValueError("stage runner returned a result for the wrong stage")
        executions.append(result)
        if result.outcome in {StageOutcome.BLOCKED, StageOutcome.FAILED}:
            break
    return ExperimentExecution(coordinate=coordinate, recipe=recipe, stages=tuple(executions))


def execute_campaign(
    *,
    campaign: CampaignPlan,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root: Path,
) -> CampaignExecution:
    provenance = ExecutionProvenance(
        plan_digest=campaign.plan_digest,
        campaign_digest=campaign.digest,
        protocol_digest=protocol_digest(),
    )
    experiments = tuple(
        execute_experiment(
            coordinate=entry.coordinate,
            provenance=provenance,
            stage_runner=stage_runner,
            output_store=output_store,
            output_root=output_root,
        )
        for entry in campaign.entries
    )
    return CampaignExecution(campaign_digest=campaign.digest, experiments=experiments)


@dataclass(frozen=True, slots=True)
class CompletionRecordOutputStore:
    def state(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExistingExperimentState:
        directory = experiment_output_directory(output_root, coordinate)
        if not directory.is_dir():
            return ExistingExperimentState.ABSENT
        record = read_completion_record(directory)
        if record is None or record.state is not CompletionState.COMPLETE:
            return ExistingExperimentState.INCOMPLETE
        observed = _observed_artifacts(output_root, record.artifacts)
        validation = validate_reload(root=output_root, completion=record, observed=observed)
        return ExistingExperimentState.COMPLETE_VALID if validation.valid else ExistingExperimentState.COMPLETE_INVALID

    def delete(self, coordinate: ExperimentCoordinate, output_root: Path) -> None:
        directory = experiment_output_directory(output_root, coordinate)
        if directory.exists():
            rmtree(directory)


def _observed_artifacts(output_root: Path, declared: tuple[ArtifactRecord, ...]) -> tuple[ArtifactRecord, ...]:
    return tuple(
        ArtifactRecord(
            kind=item.kind,
            relative_path=item.relative_path,
            checksum=checksum_file(output_root / item.relative_path),
            byte_count=ByteCount((output_root / item.relative_path).stat().st_size),
            state=ArtifactState.PUBLISHED,
        )
        for item in declared
        if (output_root / item.relative_path).is_file()
    )


@dataclass
class PipelineStageRunner:
    """Coordinates services through one cached :class:`ExperimentWorkspace` per coordinate."""

    observation_hook: ObservationHook | None = None
    _workspace: ExperimentWorkspace | None = field(default=None, init=False, repr=False)

    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
        output_root: Path,
    ) -> StageExecution:
        try:
            return self._run(stage, coordinate, provenance, output_root)
        except ScientificContractError as error:
            return StageExecution(stage=stage, outcome=StageOutcome.BLOCKED, evidence=str(error))

    def _workspace_for(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExperimentWorkspace:
        if (
            self._workspace is None
            or self._workspace.coordinate != coordinate
            or self._workspace.output_root != output_root
        ):
            self._workspace = ExperimentWorkspace(coordinate=coordinate, output_root=output_root)
        return self._workspace

    def _run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
        output_root: Path,
    ) -> StageExecution:
        if coordinate.temporal_state is not None:
            raise ScientificContractError(
                "temporal coordinates require the paired temporal execution route",
                subject=coordinate.temporal_state,
            )
        workspace = self._workspace_for(coordinate, output_root)
        match stage:
            case PipelineStage.PREFLIGHT:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=f"coordinate validated: {coordinate.stable_key}",
                )
            case PipelineStage.MATERIALIZE_DATASET:
                return self._materialize_dataset(stage, coordinate)
            case PipelineStage.CONSTRUCT_POPULATION:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=(
                        f"clients={len(workspace.context.clients)} "
                        f"split_checksum={workspace.context.split_manifest_checksum.value}"
                    ),
                )
            case PipelineStage.FIT_PREPROCESSING:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=f"state_set={workspace.context.preprocessing_state_set_checksum.value}",
                )
            case PipelineStage.TRAIN_DETECTOR:
                return self._train_detector(stage, workspace)
            case PipelineStage.SELECT_CHECKPOINT:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.COMPLETED,
                    evidence=f"selected_round={workspace.selected_checkpoint.round_number.value}",
                )
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
            case PipelineStage.VERIFY_ANCHOR:
                return self._verify_anchor(stage, coordinate, workspace)
            case PipelineStage.FINALIZE_PUBLICATION:
                return self._finalize_publication(stage, coordinate, provenance, output_root, workspace)
            case PipelineStage.PUBLISH_REPORT:
                raise ScientificContractError(
                    "report publication is a campaign-level responsibility",
                    subject=coordinate.experiment,
                )

    def _materialize_dataset(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        result = materialize_dataset(MaterializeDatasetRequest(data_root=DATA_ROOT, datasets=(coordinate.dataset,)))
        publication = result.publications[0]
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"{publication.dataset.value} status={publication.publication_status.value}",
        )

    def _train_detector(self, stage: PipelineStage, workspace: ExperimentWorkspace) -> StageExecution:
        result = workspace.training
        outcome = (
            StageOutcome.COMPLETED if result.publication_status is PublicationStatus.PUBLISHED else StageOutcome.REUSED
        )
        return StageExecution(
            stage=stage,
            outcome=outcome,
            evidence=f"rounds={len(result.candidates)} status={result.publication_status.value}",
        )

    def _observe(self, boundary: ObservationBoundary, coordinate: ExperimentCoordinate, checksum: Checksum) -> None:
        observe_graph_boundary(
            ObservationContext(boundary=boundary, coordinate=coordinate, input_checksum=checksum),
            self.observation_hook,
        )

    def _generate_scores(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        checksum = canonical_checksum(FixedScoreInvariant.from_manifest(workspace.scores))
        self._observe(ObservationBoundary.AFTER_SCORE_GENERATION_BEFORE_CALIBRATION, coordinate, checksum)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"score_invariant={checksum.value}",
        )

    def _build_calibration(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        eligible = workspace.eligible_calibration_scores()
        checksum = canonical_checksum(eligible)
        self._observe(ObservationBoundary.AFTER_CALIBRATION_BEFORE_THRESHOLD_CONSTRUCTION, coordinate, checksum)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"eligible_clients={len(eligible)} checksum={checksum.value}",
        )

    def _construct_thresholds(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        checksum = canonical_checksum(workspace.threshold)
        self._observe(ObservationBoundary.AFTER_THRESHOLD_CONSTRUCTION_BEFORE_EVALUATION, coordinate, checksum)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"threshold_checksum={checksum.value}",
        )

    def _evaluate_detector(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        evaluation = workspace.evaluation
        self._observe(
            ObservationBoundary.AFTER_EVALUATION_BEFORE_ANALYSIS,
            coordinate,
            evaluation.complete_digest,
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"complete_digest={evaluation.complete_digest.value}",
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
            evidence=f"metric={coordinate.metric.value} status={result.status.value}",
        )

    def _verify_anchor(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        if coordinate.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ScientificContractError(
                "the anchor gate applies only to the historical reproduction experiment",
                subject=coordinate.experiment,
            )
        result = verify_anchor(
            VerifyAnchorStageRequest(
                protocol=ANCHOR_DECISION_PROTOCOL,
                diagnostics_directory=(workspace.run_directory() / EvaluationRunAssetDirectory.ANCHOR.value),
                observations=None,
                historical_sources=None,
                request_independent_reproduction=False,
            )
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"gate={result.status.gate_status.value} readiness={result.status.dependent_readiness.value}",
        )

    def _finalize_publication(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
        output_root: Path,
        workspace: ExperimentWorkspace,
    ) -> StageExecution:
        selected = workspace.selection.selected
        evaluation_document_path = (
            workspace.run_directory()
            / EvaluationRunAssetDirectory.EVALUATION.value
            / FederatedEvaluationAssetName.DOCUMENT
        )
        if not evaluation_document_path.is_file():
            raise ScientificContractError(
                "finalization requires a completed evaluation document",
                subject=coordinate.experiment,
            )
        artifacts = (
            ArtifactRecord(
                kind=ArtifactKind.MODEL_TENSORS,
                relative_path=selected.tensor_path.relative_to(output_root),
                checksum=selected.tensor_checksum,
                byte_count=ByteCount(selected.tensor_path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            ),
            ArtifactRecord(
                kind=ArtifactKind.MANIFEST,
                relative_path=evaluation_document_path.relative_to(output_root),
                checksum=checksum_file(evaluation_document_path),
                byte_count=ByteCount(evaluation_document_path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            ),
        )
        directory = experiment_output_directory(output_root, coordinate)
        record = build_completion_record(
            plan_digest=provenance.plan_digest,
            campaign_digest=provenance.campaign_digest,
            artifacts=artifacts,
        )
        write_completion_record(directory, record)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"completion_state={record.state.value} artifacts={len(record.artifacts)}",
        )
