"""Federated and centralized held-out detector evaluation."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

import numpy as np

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    CentralizedThresholdMethod,
    ContractSubject,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    PublicationStatus,
    ScoreFrameColumn,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import Checksum, MetricValue, RowCount, ThresholdValue
from datp_core.evaluation.cohorts import EvaluationCohortManifest
from datp_core.evaluation.communication import CommunicationMessageDiagnostic
from datp_core.evaluation.controls import FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, PopulationMetricResult
from datp_core.evaluation.population import (
    ConformalCoverageStageInput,
    EvaluationDiagnostics,
    FederatedEvaluationArtifacts,
    FederatedEvaluationAssetName,
    FederatedEvaluationRequest,
    ThresholdEstimationStageInput,
    federated_evaluation_is_reusable,
    load_reused_federated_evaluation,
    prepare_federated_evaluation,
    rebase_federated_evaluation,
    write_federated_evaluation,
)
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.pipeline.construct_thresholds import PooledThresholdResult, threshold_result_checksum
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.generate_scores import PooledScoreArtifact, load_score_frame, reject_non_finite_scores
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.pipeline.publication.serialization import serialize_json_model
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.inference import ScoreArtifactManifest
from datp_core.thresholding.common import ThresholdConstructionResult

BENIGN_OUTCOME_LABEL = PopulationOutcomeLabel.BENIGN
ATTACK_OUTCOME_LABEL = PopulationOutcomeLabel.ATTACK
BINARY_CLASS_AVERAGE_WEIGHT = 0.5
F1_HARMONIC_MEAN_FACTOR = 2.0
RANK_MIDPOINT_WEIGHT = 0.5
ONE_BASED_RANK_OFFSET = 1.0
MANN_WHITNEY_PAIR_FACTOR = 2.0


class CentralizedDecisionRule(StrEnum):
    SCORE_STRICTLY_GREATER_THAN_THRESHOLD = "score_strictly_greater_than_threshold"


class CentralizedEvaluationPublicationAsset(StrEnum):
    EVALUATION = "centralized_evaluation.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class CentralizedConfusionCounts:
    true_negative: RowCount
    false_positive: RowCount
    true_positive: RowCount
    false_negative: RowCount

    def __post_init__(self) -> None:
        for name, value in (
            ("true_negative", self.true_negative),
            ("false_positive", self.false_positive),
            ("true_positive", self.true_positive),
            ("false_negative", self.false_negative),
        ):
            if not isinstance(value, RowCount):
                raise TypeError(f"{name} must be a RowCount")


@dataclass(frozen=True, slots=True)
class CentralizedMetricRecord:
    metric: MetricId
    status: AvailabilityStatus
    value: MetricValue | None

    def __post_init__(self) -> None:
        if self.status is AvailabilityStatus.AVAILABLE:
            if self.value is None:
                raise ValueError("available metrics require a numeric value")
        elif self.value is not None:
            raise ValueError("unavailable or undefined metrics must not carry a numeric value")


CENTRALIZED_POOLED_METRICS = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
    MetricId.POOLED_MACRO_F1,
)


@dataclass(frozen=True, slots=True)
class CentralizedEvaluationResult:
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: CentralizedConfusionCounts
    metrics: tuple[CentralizedMetricRecord, ...]
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole
    score_artifact_checksum: Checksum
    threshold_checksum: Checksum

    def __post_init__(self) -> None:
        if self.threshold_method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
            raise ScientificContractError(
                "centralized evaluation requires the pooled benign quantile threshold",
                subject=self.threshold_method,
            )
        if self.evidence_role is EvidenceRole.CONFIRMATORY:
            raise ScientificContractError(
                "centralized evaluation cannot claim confirmatory evidence role",
                subject=self.evidence_role,
            )
        if tuple(record.metric for record in self.metrics) != CENTRALIZED_POOLED_METRICS:
            raise ScientificContractError(
                "centralized evaluation metrics must follow the declared pooled metric order",
                subject=ContractSubject.METRICS,
            )


class CentralizedMetricDocument(StrictModel):
    metric: MetricId
    status: AvailabilityStatus
    value: MetricValue | None


class CentralizedEvaluationDocument(StrictModel):
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: CentralizedConfusionCounts
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole
    score_artifact_checksum: Checksum
    threshold_checksum: Checksum
    metrics: tuple[CentralizedMetricDocument, ...]

    @classmethod
    def from_result(cls, result: CentralizedEvaluationResult) -> "CentralizedEvaluationDocument":
        return cls(
            coordinate=result.coordinate,
            threshold_method=result.threshold_method,
            decision_rule=result.decision_rule,
            threshold=result.threshold,
            confusion=result.confusion,
            evaluation_row_count=result.evaluation_row_count,
            evidence_role=result.evidence_role,
            score_artifact_checksum=result.score_artifact_checksum,
            threshold_checksum=result.threshold_checksum,
            metrics=tuple(
                CentralizedMetricDocument(metric=record.metric, status=record.status, value=record.value)
                for record in result.metrics
            ),
        )


@dataclass(frozen=True, slots=True)
class CentralizedEvaluationPublicationRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedDetectorRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    evaluation: CentralizedEvaluationResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorRequest:
    score_manifest: ScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    comparison_fixed_score_evidence: FixedScoreEvidence | None
    evidence_role: EvidenceRole
    conformal_coverage_inputs: tuple[ConformalCoverageStageInput, ...]
    threshold_estimation_inputs: tuple[ThresholdEstimationStageInput, ...]
    communication_messages: tuple[CommunicationMessageDiagnostic, ...]
    traffic_rate_evidence: ValidatedTrafficRateEvidence | None
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None = None
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum


def evaluate_federated_detector(request: EvaluateFederatedDetectorRequest) -> EvaluateFederatedDetectorResult:
    prepared = prepare_federated_evaluation(
        FederatedEvaluationRequest(
            score_manifest=request.score_manifest,
            threshold_result=request.threshold_result,
            cohort=request.cohort,
            fixed_score_evidence=request.fixed_score_evidence,
            comparison_fixed_score_evidence=request.comparison_fixed_score_evidence,
            evidence_role=request.evidence_role,
            conformal_coverage_inputs=request.conformal_coverage_inputs,
            threshold_estimation_inputs=request.threshold_estimation_inputs,
            communication_messages=request.communication_messages,
            traffic_rate_evidence=request.traffic_rate_evidence,
            temporal_provenance=request.temporal_provenance,
            temporal_threshold_provenance=request.temporal_threshold_provenance,
            execution_identity=request.execution_identity,
        )
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=write_federated_evaluation,
                validator=federated_evaluation_is_reusable,
                loader=load_reused_federated_evaluation,
                rebaser=rebase_federated_evaluation,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedEvaluationAssetName.COMPLETE,
        )
    )
    artifacts: FederatedEvaluationArtifacts = publication.value
    return EvaluateFederatedDetectorResult(
        stage=PipelineStage.EVALUATE_DETECTOR,
        publication_status=publication.status,
        clients=artifacts.clients,
        population=artifacts.population,
        diagnostics=artifacts.diagnostics,
        complete_digest=publication.complete_digest,
    )


def evaluate_centralized_detector(request: EvaluateCentralizedDetectorRequest) -> EvaluateCentralizedDetectorResult:
    publication_request = CentralizedEvaluationPublicationRequest(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold=request.threshold,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_evaluation,
                validator=centralized_evaluation_is_reusable,
                loader=load_reused_centralized_evaluation,
                rebaser=rebase_centralized_evaluation,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedEvaluationPublicationAsset.COMPLETE,
        )
    )
    return EvaluateCentralizedDetectorResult(
        stage=PipelineStage.EVALUATE_DETECTOR,
        publication_status=publication.status,
        evaluation=publication.value,
        complete_digest=publication.complete_digest,
    )


def evaluate_centralized_reference(
    *,
    coordinate: CentralizedTrainingCoordinate,
    evaluation_scores: PooledScoreArtifact,
    threshold_result: PooledThresholdResult,
) -> CentralizedEvaluationResult:
    _validate_evaluation_inputs(coordinate, evaluation_scores, threshold_result)
    labels, scores = _evaluation_arrays(evaluation_scores)
    predictions = scores > threshold_result.threshold.value
    confusion = _confusion_counts(labels, predictions)
    metrics = _pooled_metrics(labels, scores, confusion)
    return CentralizedEvaluationResult(
        coordinate=coordinate,
        threshold_method=threshold_result.method,
        decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
        threshold=threshold_result.threshold,
        confusion=confusion,
        metrics=metrics,
        evaluation_row_count=RowCount(int(scores.shape[0])),
        evidence_role=EvidenceRole.SUPPORTIVE,
        score_artifact_checksum=evaluation_scores.checksum,
        threshold_checksum=threshold_result_checksum(threshold_result),
    )


def write_centralized_evaluation(
    request: CentralizedEvaluationPublicationRequest,
    directory: Path,
) -> CentralizedEvaluationResult:
    evaluation = evaluate_centralized_publication(request)
    write_evaluation_document(evaluation, directory)
    (directory / CentralizedEvaluationPublicationAsset.COMPLETE).write_text(
        evaluation_result_checksum(evaluation).value,
        encoding="utf-8",
    )
    return evaluation


def centralized_evaluation_is_reusable(
    request: CentralizedEvaluationPublicationRequest,
    directory: Path,
) -> bool:
    complete = directory / CentralizedEvaluationPublicationAsset.COMPLETE
    document = directory / CentralizedEvaluationPublicationAsset.EVALUATION
    if not complete.is_file() or not document.is_file():
        return False
    expected = evaluation_result_checksum(evaluate_centralized_publication(request))
    try:
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except OSError:
        return False


def load_reused_centralized_evaluation(
    request: CentralizedEvaluationPublicationRequest,
    directory: Path,
) -> CentralizedEvaluationResult:
    del directory
    return evaluate_centralized_publication(request)


def rebase_centralized_evaluation(
    result: CentralizedEvaluationResult,
    directory: Path,
) -> CentralizedEvaluationResult:
    del directory
    return result


def evaluate_centralized_publication(
    request: CentralizedEvaluationPublicationRequest,
) -> CentralizedEvaluationResult:
    return evaluate_centralized_reference(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold_result=request.threshold,
    )


def write_evaluation_document(evaluation: CentralizedEvaluationResult, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CentralizedEvaluationPublicationAsset.EVALUATION
    serialize_json_model(CentralizedEvaluationDocument.from_result(evaluation), path)
    return path


def evaluation_result_checksum(result: CentralizedEvaluationResult) -> Checksum:
    return canonical_checksum(result)


def reject_centralized_result_in_confirmatory_threshold_comparison(result: CentralizedEvaluationResult) -> None:
    raise LeakageError(
        "centralized reference evaluation cannot enter the confirmatory shared-versus-local threshold comparison",
        subject=result.threshold_method,
    )


def reject_centralized_as_federated_threshold_policy(method: CentralizedThresholdMethod) -> None:
    raise LeakageError("centralized pooled quantile is not a federated threshold policy", subject=method)


def reject_cross_client_cv_fpr_from_pooled_centralized() -> None:
    raise LeakageError(
        "confirmatory cross-client CV(FPR) cannot be computed from the pooled centralized result",
        subject=MetricId.FPR_COEFFICIENT_OF_VARIATION,
    )


def reject_centralized_in_federated_threshold_comparison(method: FederatedThresholdMethod) -> None:
    raise LeakageError(
        "centralized reference cannot be inserted into federated threshold-policy comparisons",
        subject=method,
    )


def _validate_evaluation_inputs(
    coordinate: CentralizedTrainingCoordinate,
    evaluation_scores: PooledScoreArtifact,
    threshold_result: PooledThresholdResult,
) -> None:
    if evaluation_scores.coordinate != coordinate or threshold_result.coordinate != coordinate:
        raise ScientificContractError("evaluation coordinate mismatch", subject=ContractSubject.COORDINATE)
    if evaluation_scores.partition_role is not PartitionRole.EVALUATION:
        raise ScientificContractError(
            "centralized evaluation requires evaluation scores",
            subject=evaluation_scores.partition_role,
        )
    if threshold_result.method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
        raise ScientificContractError(
            "centralized evaluation requires the pooled benign quantile",
            subject=threshold_result.method,
        )
    if (
        evaluation_scores.checkpoint_round != threshold_result.checkpoint_round
        or evaluation_scores.checkpoint_checksum != threshold_result.checkpoint_checksum
    ):
        raise ScientificContractError(
            "centralized threshold and evaluation scores must share one frozen checkpoint",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )


def _evaluation_arrays(evaluation_scores: PooledScoreArtifact) -> tuple[np.ndarray, np.ndarray]:
    frame = load_score_frame(evaluation_scores)
    labels = np.asarray(frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list(), dtype=object)
    scores = np.asarray(frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list(), dtype=np.float64)
    if scores.shape[0] != labels.shape[0]:
        raise ScientificContractError("evaluation scores and labels must align", subject=ContractSubject.ROWS)
    reject_non_finite_scores(scores, message="evaluation scores must be finite", subject=ContractSubject.SCORES)
    return labels, scores


def _confusion_counts(labels: np.ndarray, predictions: np.ndarray) -> CentralizedConfusionCounts:
    true_negative = false_positive = true_positive = false_negative = 0
    for label, predicted_attack in zip(labels.tolist(), predictions.tolist(), strict=True):
        label_text = str(label)
        if label_text == BENIGN_OUTCOME_LABEL:
            false_positive += int(predicted_attack)
            true_negative += int(not predicted_attack)
        elif label_text == ATTACK_OUTCOME_LABEL:
            true_positive += int(predicted_attack)
            false_negative += int(not predicted_attack)
        else:
            raise ScientificContractError(
                f"unrecognized evaluation label {label_text!r}",
                subject=ContractSubject.LABEL,
            )
    return CentralizedConfusionCounts(
        true_negative=RowCount(true_negative),
        false_positive=RowCount(false_positive),
        true_positive=RowCount(true_positive),
        false_negative=RowCount(false_negative),
    )


def _pooled_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    confusion: CentralizedConfusionCounts,
) -> tuple[CentralizedMetricRecord, ...]:
    false_positive_rate = _rate_metric(
        MetricId.FALSE_POSITIVE_RATE,
        confusion.false_positive,
        confusion.false_positive + confusion.true_negative,
    )
    true_positive_rate = _rate_metric(
        MetricId.TRUE_POSITIVE_RATE,
        confusion.true_positive,
        confusion.true_positive + confusion.false_negative,
    )
    return (
        false_positive_rate,
        true_positive_rate,
        _balanced_accuracy(false_positive_rate, true_positive_rate),
        _macro_f1_record(MetricId.BINARY_MACRO_F1, confusion),
        _auroc(labels, scores),
        _macro_f1_record(MetricId.POOLED_MACRO_F1, confusion),
    )


def _rate_metric(metric: MetricId, numerator: RowCount, denominator: RowCount) -> CentralizedMetricRecord:
    if denominator == 0:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNAVAILABLE, value=None)
    return CentralizedMetricRecord(
        metric=metric,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(numerator.value / denominator.value),
    )


def _balanced_accuracy(
    fpr: CentralizedMetricRecord,
    tpr: CentralizedMetricRecord,
) -> CentralizedMetricRecord:
    if (
        fpr.status is not AvailabilityStatus.AVAILABLE
        or tpr.status is not AvailabilityStatus.AVAILABLE
        or fpr.value is None
        or tpr.value is None
    ):
        return CentralizedMetricRecord(
            metric=MetricId.BALANCED_ACCURACY,
            status=AvailabilityStatus.UNAVAILABLE,
            value=None,
        )
    specificity = 1.0 - fpr.value.value
    return CentralizedMetricRecord(
        metric=MetricId.BALANCED_ACCURACY,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(BINARY_CLASS_AVERAGE_WEIGHT * (tpr.value.value + specificity)),
    )


def _macro_f1_record(metric: MetricId, confusion: CentralizedConfusionCounts) -> CentralizedMetricRecord:
    denominators = (
        confusion.true_positive + confusion.false_positive,
        confusion.true_positive + confusion.false_negative,
        confusion.true_negative + confusion.false_negative,
        confusion.true_negative + confusion.false_positive,
    )
    if min(denominators) == 0:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNAVAILABLE, value=None)
    attack_precision = confusion.true_positive.value / denominators[0].value
    attack_recall = confusion.true_positive.value / denominators[1].value
    benign_precision = confusion.true_negative.value / denominators[2].value
    benign_recall = confusion.true_negative.value / denominators[3].value
    attack_f1 = _f1(attack_precision, attack_recall)
    benign_f1 = _f1(benign_precision, benign_recall)
    if attack_f1 is None or benign_f1 is None:
        return CentralizedMetricRecord(metric=metric, status=AvailabilityStatus.UNDEFINED, value=None)
    return CentralizedMetricRecord(
        metric=metric,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(BINARY_CLASS_AVERAGE_WEIGHT * (attack_f1 + benign_f1)),
    )


def _f1(precision: float, recall: float) -> float | None:
    total = precision + recall
    if total == 0:
        return None
    return F1_HARMONIC_MEAN_FACTOR * precision * recall / total


def _auroc(labels: np.ndarray, scores: np.ndarray) -> CentralizedMetricRecord:
    binary = np.asarray(
        [
            1 if str(label) == ATTACK_OUTCOME_LABEL else 0 if str(label) == BENIGN_OUTCOME_LABEL else -1
            for label in labels
        ]
    )
    if np.any(binary < 0):
        raise ScientificContractError("AUROC encountered unrecognized labels", subject=ContractSubject.LABEL)
    if binary.min() == binary.max():
        return CentralizedMetricRecord(metric=MetricId.AUROC, status=AvailabilityStatus.UNAVAILABLE, value=None)
    order = np.argsort(scores, kind="mergesort")
    sorted_labels = binary[order]
    sorted_scores = scores[order]
    positive_count = float(binary.sum())
    negative_count = float(binary.size - positive_count)
    if positive_count == 0.0 or negative_count == 0.0:
        return CentralizedMetricRecord(metric=MetricId.AUROC, status=AvailabilityStatus.UNAVAILABLE, value=None)
    ranks = _average_ranks(sorted_scores)
    positive_rank_sum = float(ranks[sorted_labels == 1].sum())
    auc = (
        positive_rank_sum - positive_count * (positive_count + ONE_BASED_RANK_OFFSET) / MANN_WHITNEY_PAIR_FACTOR
    ) / (positive_count * negative_count)
    if not isfinite(auc):
        return CentralizedMetricRecord(metric=MetricId.AUROC, status=AvailabilityStatus.UNDEFINED, value=None)
    return CentralizedMetricRecord(
        metric=MetricId.AUROC,
        status=AvailabilityStatus.AVAILABLE,
        value=MetricValue(auc),
    )


def _average_ranks(sorted_scores: np.ndarray) -> np.ndarray:
    ranks = np.empty(sorted_scores.shape[0], dtype=np.float64)
    start = 0
    while start < sorted_scores.shape[0]:
        end = start + 1
        while end < sorted_scores.shape[0] and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average = RANK_MIDPOINT_WEIGHT * (start + end - 1) + ONE_BASED_RANK_OFFSET
        ranks[start:end] = average
        start = end
    return ranks
