"""Cached orchestration for one federated experiment coordinate."""

from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path

from datp_core.datasets.registry import population_capabilities
from datp_core.domain.enums import PartitionRole
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    ClientCount,
    FeatureNameSequence,
)
from datp_core.evaluation.controls import FixedScoreEvidence, build_federated_evaluation_inputs, validate_fixed_score_controls
from datp_core.evaluation.population import FederatedEvaluationAssetName, FederatedEvaluationDocument
from datp_core.learning.federated.checkpoints.selection import CheckpointDecision
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.checkpoints.service import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
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
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory, ExecutionArtifactDirectory
from datp_core.pipeline.execution.scoring import eligible_calibration_scores, load_evaluation_document, score_selected_checkpoint
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest
from datp_core.pipeline.training.federated import (
    TrainFederatedDetectorRequest,
    TrainFederatedDetectorResult,
    train_federated_detector,
)
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    LEARNING_RATE,
    resolve_single_model_federated_training_protocol,
)
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.models import ThresholdConstructionResult
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores


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

    @cached_property
    def threshold(self) -> ThresholdConstructionResult:
        result = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    self.coordinate.threshold_method,
                    self.scores.coordinate,
                    CANONICAL_QUANTILE,
                    population_capabilities(self.coordinate.population),
                    self.eligible_calibration_scores(),
                    self.context.family_by_client,
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
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=self.context.execution_identity,
                output_directory=self.run_directory() / EvaluationRunAssetDirectory.EVALUATION,
                overwrite=False,
            )
        )

    def evaluation_document(self) -> FederatedEvaluationDocument:
        return load_evaluation_document(
            self.run_directory() / EvaluationRunAssetDirectory.EVALUATION / FederatedEvaluationAssetName.DOCUMENT
        )
