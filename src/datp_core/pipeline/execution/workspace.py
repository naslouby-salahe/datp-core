"""Cached orchestration for one federated experiment coordinate."""

from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.datasets.registry import population_capabilities
from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    PartitionRole,
    ScoreFrameColumn,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import checksum_file
from datp_core.domain.values.counts import (
    CalibrationSize,
    ClientCount,
    ReplicateIndex,
)
from datp_core.domain.values.identifiers import FeatureNameSequence, StableRowId
from datp_core.domain.values.ratios import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    Quantile,
    ScoreValue,
)
from datp_core.evaluation.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    SerializedPayloadEvidence,
    ThresholdPayloadKind,
)
from datp_core.evaluation.federated.contracts import (
    CalibrationSizeAblationCell,
    ConformalCoverageStageInput,
    FederatedEvaluationDocument,
    ThresholdEstimationStageInput,
)
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.evaluation.fixed_score.construction import build_federated_evaluation_inputs
from datp_core.evaluation.fixed_score.contracts import FixedScoreEvidence
from datp_core.evaluation.fixed_score.validation import validate_fixed_score_controls
from datp_core.evaluation.models import HeldOutBenignScore
from datp_core.evaluation.threshold_estimation import ThresholdEstimationProvenance
from datp_core.evaluation.threshold_evidence import verify_held_out_benign_scores
from datp_core.learning.federated.checkpoints.selection import CheckpointDecision
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.checkpoints.service import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.decision.calibration import (
    BuildCalibrationResult,
    ConstructCalibrationSizeAblationRequest,
    build_declared_calibration,
    construct_calibration_size_ablation,
)
from datp_core.pipeline.decision.federated import (
    ConstructFederatedThresholdsRequest,
    EvaluateFederatedDetectorRequest,
    EvaluateFederatedDetectorResult,
    construct_federated_thresholds,
    evaluate_federated_detector,
)
from datp_core.pipeline.execution.context import (
    FederatedExecutionContext,
    client_scoring_inputs,
    client_training_inputs,
    resolve_execution_context,
    training_autoencoder,
    training_feature_names,
)
from datp_core.pipeline.execution.evidence import eligible_calibration_scores, load_evaluation_document
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory, ExecutionArtifactDirectory
from datp_core.pipeline.execution.score_generation import score_selected_checkpoint
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest, FederatedScoreRecord
from datp_core.pipeline.training.federated import (
    TrainFederatedDetectorRequest,
    TrainFederatedDetectorResult,
    train_federated_detector,
)
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    LEARNING_RATE,
    AutoencoderProtocol,
    resolve_single_model_federated_training_protocol,
)
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.methods.conformal import ConformalAssignment, ConformalThresholdResult
from datp_core.thresholding.methods.shrinkage import ShrinkageAssignment
from datp_core.thresholding.models import ThresholdConstructionResult
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores, exact_empirical_quantile


@dataclass(kw_only=True)
class ExperimentWorkspace:
    """Resolve each expensive coordinate-bound operation once and cache its result."""

    coordinate: ExperimentCoordinate
    output_root: Path

    @cached_property
    def context(self) -> FederatedExecutionContext:
        return resolve_execution_context(self.coordinate, self.output_root)

    @cached_property
    def autoencoder(self) -> AutoencoderProtocol:
        return training_autoencoder(self.coordinate.dataset)

    @cached_property
    def feature_names(self) -> FeatureNameSequence:
        return training_feature_names(self.coordinate.dataset)

    @cached_property
    def training(self) -> TrainFederatedDetectorResult:
        protocol = resolve_single_model_federated_training_protocol(
            model=self.context.coordinate.model,
            coefficient=self.context.coordinate.model_coefficient,
        )
        return train_federated_detector(
            TrainFederatedDetectorRequest(
                request=FederatedTrainingRequest(
                    coordinate=self.context.coordinate,
                    clients=client_training_inputs(
                        self.context.preprocessing.client_publications,
                        self.context.clients,
                        self.feature_names,
                    ),
                    population_client_count=ClientCount(len(self.context.clients)),
                    autoencoder=self.autoencoder,
                    training_protocol=protocol,
                    checkpoint_protocol=CHECKPOINT_PROTOCOL,
                    training_seed=self.context.coordinate.training_seed,
                    batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE,
                    split_manifest_checksum=self.context.split_manifest_checksum,
                    output_directory=self.context.training_directory,
                ),
                overwrite=False,
            )
        )

    @cached_property
    def selection(self) -> CheckpointDecision:
        return select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=self.context.coordinate,
                client=None,
                candidates=self.training.candidates,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=self.context.preprocessing_state_set_checksum,
                split_manifest_checksum=self.context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        )

    @cached_property
    def selected_checkpoint(self) -> CheckpointCandidate:
        return self.selection.selected

    @cached_property
    def scores(self) -> FederatedScoreArtifactManifest:
        return score_selected_checkpoint(
            checkpoint=self.selected_checkpoint,
            scored_split_protocol=self.context.coordinate.split_protocol,
            autoencoder=self.autoencoder,
            feature_names=self.feature_names,
            clients=client_scoring_inputs(self.context.preprocessing.client_publications, self.context.clients),
            output_directory=self.context.training_directory / ExecutionArtifactDirectory.SCORES,
            preprocessing_state_set_checksum=self.context.preprocessing_state_set_checksum,
            split_manifest_checksum=self.context.split_manifest_checksum,
        )

    def eligible_calibration_scores(
        self,
        role: PartitionRole = PartitionRole.CALIBRATION,
    ) -> tuple[ClientBenignCalibrationScores, ...]:
        return eligible_calibration_scores(self.scores, role)

    def run_directory(self) -> Path:
        return evaluation_run_directory(self.output_root, self.coordinate)

    @property
    def threshold_quantile(self) -> Quantile:
        if self.coordinate.threshold_quantile is not None:
            return self.coordinate.threshold_quantile
        return CANONICAL_QUANTILE

    @cached_property
    def calibration(self) -> BuildCalibrationResult | None:
        if self.coordinate.experiment is not ExperimentId.CALIBRATION_SIZE_ABLATION:
            return None
        return build_declared_calibration(self.scores)

    @cached_property
    def threshold(self) -> ThresholdConstructionResult:
        from datp_core.protocols.calibration import ClusterThresholdAggregation

        cluster_aggregation = (
            ClusterThresholdAggregation.MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
            if self.coordinate.experiment is ExperimentId.GROUP_MEDIAN_SUPPLEMENT
            and self.coordinate.threshold_method is FederatedThresholdMethod.CLUSTER_THRESHOLD
            else None
        )
        result = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    method=self.coordinate.threshold_method,
                    coordinate=self.scores.coordinate,
                    quantile=self.threshold_quantile,
                    capabilities=population_capabilities(self.coordinate.population),
                    eligible=self.eligible_calibration_scores(),
                    family_by_client=self.context.family_by_client,
                    cluster_threshold_aggregation=cluster_aggregation,
                ),
                output_directory=self.run_directory() / EvaluationRunAssetDirectory.THRESHOLD,
                overwrite=False,
            )
        ).result
        if isinstance(result, ThresholdUnavailableResult):
            raise ScientificContractError(
                f"threshold unavailable: {result.reason.value}",
                subject=self.coordinate.threshold_method,
            )
        return result

    def comparison_fixed_score_evidence(self) -> FixedScoreEvidence | None:
        reference: FixedScoreEvidence | None = None
        for method in population_capabilities(self.coordinate.population).valid_threshold_methods:
            if method is self.coordinate.threshold_method:
                continue
            comparison_coordinate = replace(self.coordinate, threshold_method=method)
            path = (
                evaluation_run_directory(self.output_root, comparison_coordinate)
                / EvaluationRunAssetDirectory.EVALUATION
                / FederatedEvaluationAssetName.DOCUMENT
            )
            if not path.is_file():
                continue
            evidence = load_evaluation_document(path).fixed_score_evidence
            if reference is None:
                reference = evidence
            else:
                validate_fixed_score_controls(
                    reference,
                    evidence,
                    auroc_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
                )
        return reference

    @cached_property
    def calibration_size_ablation(self) -> tuple[CalibrationSizeAblationCell, ...]:
        if self.coordinate.experiment is not ExperimentId.CALIBRATION_SIZE_ABLATION:
            return ()
        if self.calibration is None:
            raise ScientificContractError("calibration-size ablation requires a calibration lattice")
        inputs = build_federated_evaluation_inputs(self.scores, self.coordinate.threshold_method)
        return construct_calibration_size_ablation(
            ConstructCalibrationSizeAblationRequest(
                score_manifest=self.scores,
                method=self.coordinate.threshold_method,
                quantile=self.threshold_quantile,
                cohort=inputs.cohort,
                fixed_score_evidence=inputs.fixed_score_evidence,
                evidence_role=self.coordinate.evidence_role,
                family_by_client=self.context.family_by_client,
                calibration=self.calibration,
                execution_identity=self.context.execution_identity,
            )
        )

    def _read_benign_evaluation_scores(
        self,
        record: FederatedScoreRecord,
        client: ClientIdentity,
    ) -> tuple[HeldOutBenignScore, ...]:
        if not record.path.is_file() or checksum_file(record.path) != record.checksum:
            raise ScientificContractError("evaluation score provenance is unavailable or changed")
        frame = pl.read_parquet(record.path).filter(
            pl.col(ScoreFrameColumn.OUTCOME_LABEL.value)
            == PopulationOutcomeLabel.BENIGN.value
        )
        return tuple(
            HeldOutBenignScore(
                client=client,
                stable_row_id=StableRowId(str(row[0])),
                score=ScoreValue(float(row[1])),
                partition_role=record.partition_role,
                outcome_label=PopulationOutcomeLabel(str(row[2])),
                score_record=record,
            )
            for row in frame.select(
                (
                    ScoreFrameColumn.STABLE_ROW_ID.value,
                    ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
                    ScoreFrameColumn.OUTCOME_LABEL.value,
                )
            ).iter_rows()
        )

    def _conformal_coverage_inputs(self) -> tuple[ConformalCoverageStageInput, ...]:
        if not isinstance(self.threshold, ConformalThresholdResult):
            return ()
        threshold_result = self.threshold
        client_scores: dict[ClientIdentity, list[HeldOutBenignScore]] = {}
        for record in self.scores.evaluation_records:
            scores = self._read_benign_evaluation_scores(record, record.scored_client)
            client_scores.setdefault(record.scored_client, []).extend(scores)
        inputs: list[ConformalCoverageStageInput] = []
        for assignment in threshold_result.assignments:
            held_out = tuple(client_scores.get(assignment.client, ()))
            inputs.append(
                ConformalCoverageStageInput(
                    assignment=assignment,
                    target_coverage=threshold_result.coverage,
                    held_out_benign_scores=held_out,
                )
            )
        return tuple(inputs)

    def _threshold_estimation_inputs(self) -> tuple[ThresholdEstimationStageInput, ...]:
        if isinstance(self.threshold, (ConformalThresholdResult, ThresholdUnavailableResult)):
            return ()
        threshold_result = self.threshold
        calibration_by_client = {
            scores.client: scores
            for scores in self.eligible_calibration_scores()
        }
        client_scores: dict[ClientIdentity, list[HeldOutBenignScore]] = {}
        for record in self.scores.evaluation_records:
            scores = self._read_benign_evaluation_scores(record, record.scored_client)
            client_scores.setdefault(record.scored_client, []).extend(scores)
        all_pooled = tuple(
            item for scores in client_scores.values() for item in scores
        )
        pooled_values = np.array(
            [item.score.value for item in all_pooled], dtype=np.float64
        )
        pooled_quantile = exact_empirical_quantile(pooled_values, self.threshold_quantile)
        inputs: list[ThresholdEstimationStageInput] = []
        coordinate = self.scores.coordinate
        training_seed = coordinate.training_seed
        for assignment in threshold_result.assignments:
            client = assignment.client
            if isinstance(assignment, ShrinkageAssignment):
                estimated = assignment.blended_threshold
            elif isinstance(assignment, ConformalAssignment):
                estimated = assignment.threshold
            else:
                estimated = assignment.threshold
            calibration_scores = calibration_by_client.get(client)
            calibration_size = (
                CalibrationSize(len(calibration_scores.scores))
                if calibration_scores is not None
                else CalibrationSize(0)
            )
            provenance = ThresholdEstimationProvenance(
                client=client,
                coordinate=coordinate,
                training_seed=training_seed,
                calibration_size=calibration_size,
                replicate_index=ReplicateIndex(0),
                quantile=self.threshold_quantile,
            )
            held_out = tuple(client_scores.get(client, ()))
            verified = verify_held_out_benign_scores(
                client=client,
                coordinate=coordinate,
                scores=held_out,
            )
            inputs.append(
                ThresholdEstimationStageInput(
                    provenance=provenance,
                    estimated_threshold=estimated,
                    exact_pooled_benign_quantile_reference=pooled_quantile,
                    verified_benign_scores=verified,
                )
            )
        return tuple(inputs)

    def _communication_messages(self) -> tuple[CommunicationMessageDiagnostic, ...]:
        coordinate = self.scores.coordinate
        training_seed = coordinate.training_seed
        messages: list[CommunicationMessageDiagnostic] = []
        for round_result in self.training.training.history.rounds:
            comm = round_result.communication
            payload_bytes = bytes(comm.state_bytes.value)
            payload = SerializedPayloadEvidence(
                serialized_bytes=payload_bytes,
                logical_element_count=comm.logical_element_count,
            )
            for client_result in round_result.client_results:
                client_id = client_result.client
                messages.append(
                    CommunicationMessageDiagnostic(
                        training_seed=training_seed,
                        coordinate=coordinate,
                        sender=f"client:{client_id.client_id}",
                        receiver="coordinator",
                        direction=MessageDirection.CLIENT_TO_COORDINATOR,
                        payload_kind=ThresholdPayloadKind.MODEL_TRANSMISSION,
                        payload=payload,
                        client=client_id,
                        group_identity=None,
                        estimation_basis=comm.estimation_basis,
                    )
                )
                messages.append(
                    CommunicationMessageDiagnostic(
                        training_seed=training_seed,
                        coordinate=coordinate,
                        sender="coordinator",
                        receiver=f"client:{client_id.client_id}",
                        direction=MessageDirection.COORDINATOR_TO_CLIENT,
                        payload_kind=ThresholdPayloadKind.MODEL_TRANSMISSION,
                        payload=payload,
                        client=client_id,
                        group_identity=None,
                        estimation_basis=comm.estimation_basis,
                    )
                )
        return tuple(messages)

    @cached_property
    def evaluation(self) -> EvaluateFederatedDetectorResult:
        inputs = build_federated_evaluation_inputs(self.scores, self.coordinate.threshold_method)
        return evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                score_manifest=self.scores,
                threshold_result=self.threshold,
                cohort=inputs.cohort,
                fixed_score_evidence=inputs.fixed_score_evidence,
                comparison_fixed_score_evidence=self.comparison_fixed_score_evidence(),
                evidence_role=self.coordinate.evidence_role,
                conformal_coverage_inputs=self._conformal_coverage_inputs(),
                threshold_estimation_inputs=self._threshold_estimation_inputs(),
                communication_messages=self._communication_messages(),
                traffic_rate_evidence=None,
                execution_identity=self.context.execution_identity,
                output_directory=self.run_directory() / EvaluationRunAssetDirectory.EVALUATION,
                overwrite=False,
                calibration_size_ablation=self.calibration_size_ablation,
            )
        )

    def evaluation_document(self) -> FederatedEvaluationDocument:
        return load_evaluation_document(
            self.run_directory() / EvaluationRunAssetDirectory.EVALUATION / FederatedEvaluationAssetName.DOCUMENT
        )
