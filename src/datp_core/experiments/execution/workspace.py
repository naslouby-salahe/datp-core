"""Cached orchestration for one federated experiment coordinate."""

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.analysis.metrics.federated import (
    CalibrationSizeAblationCell,
    ConformalCoverageStageInput,
    FederatedEvaluationDocument,
    ThresholdEstimationStageInput,
)
from datp_core.analysis.metrics.federated_publication import (
    EvaluateFederatedDetectorRequest,
    EvaluateFederatedDetectorResult,
    evaluate_federated_detector,
)
from datp_core.analysis.metrics.fixed_score_construction import build_federated_evaluation_inputs
from datp_core.analysis.metrics.models import HeldOutBenignScore
from datp_core.analysis.metrics.threshold_estimation import ThresholdEstimationProvenance
from datp_core.analysis.metrics.threshold_evidence import verify_held_out_benign_scores
from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    SerializedPayloadEvidence,
    ThresholdPayloadKind,
)
from datp_core.analysis.operational.traffic_rates import traffic_rate_evidence_for_population
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.thresholds import (
    FederatedThresholdConstructionRequest,
    construct_and_publish_federated_thresholds,
)
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ExperimentId,
    FeatureNameSequence,
    FederatedThresholdMethod,
    MessageEndpoint,
    PartitionRole,
    ScoreFrameColumn,
    StableRowId,
)
from datp_core.core.numeric import (
    CalibrationSize,
    ClientCount,
    Quantile,
    ReplicateIndex,
    ScoreValue,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.data.registry import population_capabilities
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest, FederatedScoreRecord
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated_publication import (
    TrainFederatedDetectorRequest,
    TrainFederatedDetectorResult,
    train_federated_detector,
)
from datp_core.detector.training.protocols import BATCH_SIZE, LEARNING_RATE
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.execution.context import (
    FederatedExecutionContext,
    client_scoring_inputs,
    client_training_inputs,
    diagnostic_snapshot_protocol_for,
    execution_context_cache_key,
    resolve_execution_context,
    training_autoencoder_for,
    training_feature_names,
    training_protocol_for,
)
from datp_core.experiments.execution.evidence import eligible_calibration_scores, load_evaluation_document
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory, ExecutionArtifactDirectory
from datp_core.experiments.execution.models import ProgressEvent, ProgressEventKind, ProgressHook
from datp_core.experiments.execution.score_generation import score_terminal_model
from datp_core.thresholds.calibration.construction import (
    BuildCalibrationResult,
    ConstructCalibrationSizeAblationRequest,
    build_declared_calibration,
    construct_calibration_size_ablation,
)
from datp_core.thresholds.contracts import ThresholdUnavailableResult
from datp_core.thresholds.dispatch import ThresholdConstructionRequest, ThresholdConstructionResult
from datp_core.thresholds.protocols import (
    CANONICAL_QUANTILE,
    CalibrationSupportRule,
    ClusterThresholdAggregation,
)
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, exact_empirical_quantile
from datp_core.thresholds.variants.conformal import ConformalThresholdResult
from datp_core.thresholds.variants.shrinkage import FixedShrinkageCurveResult


def _pooled_calibration_quantile(
    calibration_by_client: dict[ClientIdentity, ClientBenignCalibrationScores],
    quantile: Quantile,
) -> ThresholdValue:
    """Exact pooled benign quantile oracle from eligible calibration scores only.

    The threshold-estimation oracle must never consume held-out evaluation scores;
    calibration and evaluation evidence stay isolated.
    """
    pooled_values = np.asarray(
        tuple(score.value for scores in calibration_by_client.values() for score in scores.scores),
        dtype=np.float64,
    )
    return exact_empirical_quantile(pooled_values, quantile)


@dataclass(kw_only=True)
class ExperimentWorkspace:
    """Resolve each expensive coordinate-bound operation once and cache its result."""

    coordinate: ExperimentCoordinate
    output_root: Path
    progress: ProgressHook | None = None
    shared_context_cache: dict[tuple[object, ...], FederatedExecutionContext] | None = None
    shared_evaluation_cache: dict[Path, EvaluateFederatedDetectorResult] | None = None
    shared_training_cache: dict[tuple[object, ...], TrainFederatedDetectorResult] | None = None
    shared_score_cache: dict[tuple[object, ...], FederatedScoreArtifactManifest] | None = None

    @cached_property
    def context(self) -> FederatedExecutionContext:
        return self._resolve_shared_context()

    def _resolve_shared_context(self) -> FederatedExecutionContext:
        cache = self.shared_context_cache
        if cache is None:
            return resolve_execution_context(self.coordinate, self.output_root)
        key = execution_context_cache_key(self.coordinate, self.output_root)
        context = cache.get(key)
        if context is None:
            context = resolve_execution_context(self.coordinate, self.output_root)
            cache[key] = context
        return context

    @cached_property
    def autoencoder(self) -> AutoencoderProtocol:
        return training_autoencoder_for(self.coordinate)

    @cached_property
    def feature_names(self) -> FeatureNameSequence:
        return training_feature_names(self.coordinate.dataset)

    @cached_property
    def training(self) -> TrainFederatedDetectorResult:
        key = execution_context_cache_key(self.coordinate, self.output_root)
        if self.shared_training_cache is not None and (cached := self.shared_training_cache.get(key)) is not None:
            return cached
        protocol = training_protocol_for(self.coordinate)
        result = train_federated_detector(
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
                    diagnostic_snapshot_protocol=diagnostic_snapshot_protocol_for(self.coordinate),
                    training_seed=self.context.coordinate.training_seed,
                    batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE,
                    output_directory=self.context.training_directory,
                    progress_callback=self._round_progress_callback,
                ),
            )
        )
        if self.shared_training_cache is not None:
            self.shared_training_cache[key] = result
        return result

    def _round_progress_callback(self, round_number: int, maximum_round: int) -> None:
        if self.progress is not None:
            self.progress.emit(
                ProgressEvent(
                    kind=ProgressEventKind.TRAINING_ROUND,
                    coordinate=self.coordinate,
                    round_number=round_number,
                    maximum_round=maximum_round,
                )
            )

    @cached_property
    def scores(self) -> FederatedScoreArtifactManifest:
        key = execution_context_cache_key(self.coordinate, self.output_root)
        if self.shared_score_cache is not None and (cached := self.shared_score_cache.get(key)) is not None:
            return cached
        scores = score_terminal_model(
            training=self.training.training,
            scored_split_protocol=self.context.coordinate.split_protocol,
            autoencoder=self.autoencoder,
            feature_names=self.feature_names,
            clients=client_scoring_inputs(self.context.preprocessing.client_publications, self.context.clients),
            output_directory=self.context.training_directory / ExecutionArtifactDirectory.SCORES,
        )
        if self.shared_score_cache is not None:
            self.shared_score_cache[key] = scores
        return scores

    def eligible_calibration_scores(self) -> tuple[ClientBenignCalibrationScores, ...]:
        return eligible_calibration_scores(self.scores, PartitionRole.CALIBRATION)

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

    def _cluster_aggregation(self) -> ClusterThresholdAggregation | None:
        if self.coordinate.threshold_method is not FederatedThresholdMethod.CLUSTER_THRESHOLD:
            return None
        if self.coordinate.experiment is ExperimentId.GROUP_MEDIAN_SUPPLEMENT:
            return ClusterThresholdAggregation.MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
        return ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS

    @cached_property
    def threshold(self) -> ThresholdConstructionResult:
        result = construct_and_publish_federated_thresholds(
            FederatedThresholdConstructionRequest(
                request=ThresholdConstructionRequest(
                    method=self.coordinate.threshold_method,
                    coordinate=self.scores.coordinate,
                    quantile=self.threshold_quantile,
                    capabilities=population_capabilities(self.coordinate.population),
                    eligible=self.eligible_calibration_scores(),
                    family_by_client=self.context.family_by_client,
                    support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                    cluster_threshold_aggregation=self._cluster_aggregation(),
                ),
                output_directory=self.run_directory() / EvaluationRunAssetDirectory.THRESHOLD,
                overwrite=False,
            )
        ).result
        if isinstance(result, ThresholdUnavailableResult):
            raise ScientificContractError(
                ErrorMessage(f"threshold unavailable: {result.reason.value}"),
                subject=self.coordinate.threshold_method,
            )
        return result

    @cached_property
    def calibration_size_ablation(self) -> tuple[CalibrationSizeAblationCell, ...]:
        if self.coordinate.experiment is not ExperimentId.CALIBRATION_SIZE_ABLATION:
            return ()
        if self.calibration is None:
            raise ScientificContractError(ErrorMessage("calibration-size ablation requires a calibration lattice"))
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
        if not record.path.is_file():
            raise ScientificContractError(ErrorMessage("evaluation score evidence is unavailable"))
        frame = pl.read_parquet(record.path).filter(
            pl.col(ScoreFrameColumn.OUTCOME_LABEL.value) == PopulationOutcomeLabel.BENIGN.value
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
        if isinstance(
            self.threshold,
            (FixedShrinkageCurveResult, ConformalThresholdResult, ThresholdUnavailableResult),
        ):
            return ()
        threshold_result = self.threshold
        calibration_by_client = {scores.client: scores for scores in self.eligible_calibration_scores()}
        pooled_quantile = _pooled_calibration_quantile(calibration_by_client, self.threshold_quantile)
        client_scores: dict[ClientIdentity, list[HeldOutBenignScore]] = {}
        for record in self.scores.evaluation_records:
            scores = self._read_benign_evaluation_scores(record, record.scored_client)
            client_scores.setdefault(record.scored_client, []).extend(scores)
        inputs: list[ThresholdEstimationStageInput] = []
        coordinate = self.scores.coordinate
        training_seed = coordinate.training_seed
        for assignment in threshold_result.assignments:
            client = assignment.client
            estimated = assignment.threshold
            calibration_scores = calibration_by_client.get(client)
            if calibration_scores is None:
                raise ScientificContractError(
                    ErrorMessage("threshold assignment client has no eligible benign calibration evidence")
                )
            provenance = ThresholdEstimationProvenance(
                client=client,
                coordinate=coordinate,
                training_seed=training_seed,
                calibration_size=CalibrationSize(len(calibration_scores.scores)),
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
            payload = SerializedPayloadEvidence(
                serialized_byte_count=comm.state_bytes,
                logical_element_count=comm.logical_element_count,
            )
            for client_result in round_result.client_results:
                client_id = client_result.client
                messages.append(
                    CommunicationMessageDiagnostic(
                        training_seed=training_seed,
                        coordinate=coordinate,
                        sender=MessageEndpoint(f"client:{client_id.client_id.value}"),
                        receiver=MessageEndpoint("coordinator"),
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
                        sender=MessageEndpoint("coordinator"),
                        receiver=MessageEndpoint(f"client:{client_id.client_id.value}"),
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
        return self._resolve_shared_evaluation()

    def _resolve_shared_evaluation(self) -> EvaluateFederatedDetectorResult:
        cache = self.shared_evaluation_cache
        if cache is None:
            return self._evaluate()
        key = self.run_directory()
        result = cache.get(key)
        if result is None:
            result = self._evaluate()
            cache[key] = result
        return result

    def _evaluate(self) -> EvaluateFederatedDetectorResult:
        inputs = build_federated_evaluation_inputs(self.scores, self.coordinate.threshold_method)
        return evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                score_manifest=self.scores,
                threshold_result=self.threshold,
                cohort=inputs.cohort,
                fixed_score_evidence=inputs.fixed_score_evidence,
                evidence_role=self.coordinate.evidence_role,
                conformal_coverage_inputs=self._conformal_coverage_inputs(),
                threshold_estimation_inputs=self._threshold_estimation_inputs(),
                communication_messages=self._communication_messages(),
                traffic_rate_evidence=traffic_rate_evidence_for_population(self.coordinate.population),
                execution_identity=self.context.execution_identity,
                output_directory=self.run_directory() / EvaluationRunAssetDirectory.EVALUATION,
                overwrite=False,
                calibration_size_ablation=self.calibration_size_ablation,
            )
        )

    def evaluation_document(self) -> FederatedEvaluationDocument:
        return load_evaluation_document(
            self.run_directory() / EvaluationRunAssetDirectory.EVALUATION / "evaluation.json"
        )
