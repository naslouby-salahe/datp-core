"""Canonical single-coordinate stage execution and output-state ownership."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from datp_core.anchor.models import VerifyAnchorStageRequest
from datp_core.domain.enums import ExperimentId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import ByteCount, Checksum, ClientCount, checksum_file
from datp_core.evaluation.controls import build_federated_evaluation_inputs
from datp_core.evaluation.models import metric_by_id
from datp_core.evaluation.population import FederatedEvaluationAssetName, FederatedEvaluationDocument
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.construct_thresholds import ConstructFederatedThresholdsRequest, construct_federated_thresholds
from datp_core.pipeline.evaluate_detector import EvaluateFederatedDetectorRequest, evaluate_federated_detector
from datp_core.pipeline.execution import (
    ExecutionProvenance,
    ExistingExperimentState,
    PipelineStage,
    StageExecution,
    StageOutcome,
)
from datp_core.pipeline.federated_execution import (
    FederatedExecutionContext,
    eligible_calibration_scores,
    family_identities,
    load_evaluation_document,
    resolve_execution_context,
    score_execution_context,
    training_autoencoder,
    training_feature_names,
    training_protocol_for,
)
from datp_core.pipeline.materialize_dataset import MaterializeDatasetRequest, materialize_dataset
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.completion import (
    build_completion_record,
    read_completion_record,
    write_completion_record,
)
from datp_core.pipeline.publication.layout import experiment_output_directory
from datp_core.pipeline.publication.records import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactState,
    CompletionState,
)
from datp_core.pipeline.publication.reload_validation import validate_reload
from datp_core.pipeline.select_checkpoint import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.pipeline.train_detector import TrainFederatedDetectorRequest, train_federated_detector
from datp_core.pipeline.verify_anchor import verify_anchor
from datp_core.populations.capabilities import population_capabilities
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.graph import (
    ObservationBoundary,
    ObservationContext,
    ObservationHook,
    observe_graph_boundary,
)
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.protocols.runtime import DATA_ROOT, OUTPUTS_ROOT
from datp_core.protocols.training import BATCH_SIZE, CHECKPOINT_PROTOCOL, LEARNING_RATE
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult


@dataclass(frozen=True, slots=True)
class ExperimentOutputStore:
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


@dataclass(frozen=True, slots=True)
class StageRunner:
    observation_hook: ObservationHook | None = None

    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
    ) -> StageExecution:
        try:
            return self._run(stage, coordinate, provenance)
        except ScientificContractError as error:
            return StageExecution(stage=stage, outcome=StageOutcome.BLOCKED, evidence=str(error))

    def _run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
    ) -> StageExecution:
        if coordinate.temporal_state is not None:
            raise ScientificContractError(
                "temporal coordinates require the paired temporal execution route",
                subject=coordinate.temporal_state,
            )
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
                return self._construct_population(stage, coordinate)
            case PipelineStage.FIT_PREPROCESSING:
                return self._fit_preprocessing(stage, coordinate)
            case PipelineStage.TRAIN_DETECTOR:
                return self._train_detector(stage, coordinate)
            case PipelineStage.SELECT_CHECKPOINT:
                return self._select_checkpoint(stage, coordinate)
            case PipelineStage.GENERATE_SCORES:
                return self._generate_scores(stage, coordinate)
            case PipelineStage.BUILD_CALIBRATION:
                return self._build_calibration(stage, coordinate)
            case PipelineStage.CONSTRUCT_THRESHOLDS:
                return self._construct_thresholds(stage, coordinate)
            case PipelineStage.EVALUATE_DETECTOR:
                return self._evaluate_detector(stage, coordinate)
            case PipelineStage.ANALYZE_EVIDENCE:
                return self._analyze_evidence(stage, coordinate)
            case PipelineStage.VERIFY_ANCHOR:
                return self._verify_anchor(stage, coordinate)
            case PipelineStage.FINALIZE_PUBLICATION:
                return self._finalize_publication(stage, coordinate, provenance)
            case PipelineStage.PUBLISH_REPORT:
                raise ScientificContractError(
                    "report publication is a campaign-level responsibility",
                    subject=coordinate.experiment,
                )

    def _context(self, coordinate: ExperimentCoordinate) -> FederatedExecutionContext:
        return resolve_execution_context(coordinate)

    def _materialize_dataset(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        result = materialize_dataset(MaterializeDatasetRequest(data_root=DATA_ROOT, datasets=(coordinate.dataset,)))
        publication = result.publications[0]
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"{publication.dataset.value} status={publication.publication_status.value}",
        )

    def _construct_population(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        context = self._context(coordinate)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"clients={len(context.clients)} split_checksum={context.split_manifest_checksum.value}",
        )

    def _fit_preprocessing(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        context = self._context(coordinate)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"state_set={context.preprocessing_state_set_checksum.value}",
        )

    def _training(self, coordinate: ExperimentCoordinate):
        context = self._context(coordinate)
        result = train_federated_detector(
            TrainFederatedDetectorRequest(
                request=FederatedTrainingRequest(
                    coordinate=context.coordinate,
                    clients=tuple(
                        __import__("datp_core.pipeline.federated_execution", fromlist=["client_training_inputs"])
                        .client_training_inputs(
                            context.preprocessing.client_publications,
                            context.clients,
                            training_feature_names(coordinate.dataset),
                        )
                    ),
                    population_client_count=ClientCount(len(context.clients)),
                    autoencoder=training_autoencoder(coordinate.dataset),
                    training_protocol=training_protocol_for(coordinate),
                    checkpoint_protocol=CHECKPOINT_PROTOCOL,
                    training_seed=context.coordinate.training_seed,
                    batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE,
                    split_manifest_checksum=context.split_manifest_checksum,
                    output_directory=context.training_directory,
                ),
                overwrite=False,
            )
        )
        return context, result

    def _selection(self, coordinate: ExperimentCoordinate):
        context, training = self._training(coordinate)
        selection = select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=context.coordinate,
                client=None,
                candidates=training.candidates,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        )
        return context, selection

    def _train_detector(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        _, result = self._training(coordinate)
        outcome = StageOutcome.COMPLETED if result.publication_status.value == "published" else StageOutcome.REUSED
        return StageExecution(
            stage=stage,
            outcome=outcome,
            evidence=f"rounds={len(result.candidates)} status={result.publication_status.value}",
        )

    def _select_checkpoint(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        _, selection = self._selection(coordinate)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"selected_round={selection.decision.selected.round_number.value}",
        )

    def _scores(self, coordinate: ExperimentCoordinate):
        context = self._context(coordinate)
        scores = score_execution_context(
            context,
            autoencoder=training_autoencoder(coordinate.dataset),
            feature_names=training_feature_names(coordinate.dataset),
        )
        return context, scores

    def _observe(
        self,
        boundary: ObservationBoundary,
        coordinate: ExperimentCoordinate,
        checksum: Checksum,
    ) -> None:
        observe_graph_boundary(
            ObservationContext(boundary=boundary, coordinate=coordinate, input_checksum=checksum),
            self.observation_hook,
        )

    def _generate_scores(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        _, scores = self._scores(coordinate)
        checksum = canonical_checksum(FixedScoreInvariant.from_manifest(scores))
        self._observe(ObservationBoundary.AFTER_SCORE_GENERATION_BEFORE_CALIBRATION, coordinate, checksum)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"score_invariant={checksum.value}",
        )

    def _build_calibration(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        _, scores = self._scores(coordinate)
        eligible = eligible_calibration_scores(scores)
        checksum = canonical_checksum(eligible)
        self._observe(ObservationBoundary.AFTER_CALIBRATION_BEFORE_THRESHOLD_CONSTRUCTION, coordinate, checksum)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"eligible_clients={len(eligible)} checksum={checksum.value}",
        )

    def _threshold(self, coordinate: ExperimentCoordinate):
        context, scores = self._scores(coordinate)
        threshold = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    coordinate.threshold_method,
                    scores.coordinate,
                    CANONICAL_QUANTILE,
                    population_capabilities(coordinate.population),
                    eligible_calibration_scores(scores),
                    family_identities(context.clients, context.family_by_client),
                ),
                output_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "threshold",
                overwrite=False,
            )
        ).result
        if isinstance(threshold, ThresholdUnavailableResult):
            raise ScientificContractError(
                f"threshold unavailable: {threshold.reason.value}",
                subject=coordinate.threshold_method,
            )
        return context, scores, threshold

    def _construct_thresholds(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        _, _, threshold = self._threshold(coordinate)
        checksum = canonical_checksum(threshold)
        self._observe(ObservationBoundary.AFTER_THRESHOLD_CONSTRUCTION_BEFORE_EVALUATION, coordinate, checksum)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"threshold_checksum={checksum.value}",
        )

    def _evaluate_detector(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        context, scores, threshold = self._threshold(coordinate)
        evaluation_inputs = build_federated_evaluation_inputs(scores, coordinate.threshold_method)
        evaluation = evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                score_manifest=scores,
                threshold_result=threshold,
                cohort=evaluation_inputs.cohort,
                fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
                comparison_fixed_score_evidence=None,
                evidence_role=coordinate.evidence_role,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=context.execution_identity,
                output_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "evaluation",
                overwrite=False,
            )
        )
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

    def _evaluation(self, coordinate: ExperimentCoordinate) -> FederatedEvaluationDocument:
        directory = experiment_output_directory(OUTPUTS_ROOT, coordinate)
        return load_evaluation_document(directory / "evaluation" / FederatedEvaluationAssetName.DOCUMENT)

    def _analyze_evidence(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        result = metric_by_id(self._evaluation(coordinate).population.metrics, coordinate.metric)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"metric={coordinate.metric.value} status={result.status.value}",
        )

    def _verify_anchor(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        if coordinate.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ScientificContractError(
                "the anchor gate applies only to the historical reproduction experiment",
                subject=coordinate.experiment,
            )
        result = verify_anchor(
            VerifyAnchorStageRequest(
                protocol=ANCHOR_DECISION_PROTOCOL,
                diagnostics_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "anchor",
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
    ) -> StageExecution:
        _, selection = self._selection(coordinate)
        selected = selection.decision.selected
        evaluation_document_path = (
            experiment_output_directory(OUTPUTS_ROOT, coordinate) / "evaluation" / FederatedEvaluationAssetName.DOCUMENT
        )
        if not evaluation_document_path.is_file():
            raise ScientificContractError(
                "finalization requires a completed evaluation document",
                subject=coordinate.experiment,
            )
        artifacts = (
            ArtifactRecord(
                kind=ArtifactKind.MODEL_TENSORS,
                relative_path=selected.tensor_path.relative_to(OUTPUTS_ROOT),
                checksum=selected.tensor_checksum,
                byte_count=ByteCount(selected.tensor_path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            ),
            ArtifactRecord(
                kind=ArtifactKind.MANIFEST,
                relative_path=evaluation_document_path.relative_to(OUTPUTS_ROOT),
                checksum=checksum_file(evaluation_document_path),
                byte_count=ByteCount(evaluation_document_path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            ),
        )
        record = build_completion_record(
            plan_digest=provenance.plan_digest,
            campaign_digest=provenance.campaign_digest,
            artifacts=artifacts,
        )
        write_completion_record(experiment_output_directory(OUTPUTS_ROOT, coordinate), record)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"completion_state={record.state.value} artifacts={len(record.artifacts)}",
        )
