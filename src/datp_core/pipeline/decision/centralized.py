"""Pooled centralized threshold construction and held-out evaluation."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

import numpy as np

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.datasets.partitioning.integrity import reject_non_benign_labels
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
    QuantileInterpolationSemantics,
    ScoreFrameColumn,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum, canonical_json_text
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RoundNumber, RowCount
from datp_core.domain.values.identifiers import OutcomeLabel, OutcomeLabelSequence
from datp_core.domain.values.ratios import MetricValue, Quantile, ThresholdValue
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.pipeline.publication.service import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
    serialize_json_model,
)
from datp_core.pipeline.scoring.centralized import load_score_frame, reject_non_finite_scores
from datp_core.pipeline.scoring.models import PooledScoreArtifact
from datp_core.protocols.calibration import CANONICAL_QUANTILE, CentralizedQuantileProtocol

BENIGN_OUTCOME_LABEL = PopulationOutcomeLabel.BENIGN
ATTACK_OUTCOME_LABEL = PopulationOutcomeLabel.ATTACK
BINARY_CLASS_AVERAGE_WEIGHT = 0.5
F1_HARMONIC_MEAN_FACTOR = 2.0
RANK_MIDPOINT_WEIGHT = 0.5
ONE_BASED_RANK_OFFSET = 1.0
MANN_WHITNEY_PAIR_FACTOR = 2.0


class CentralizedThresholdAssetName(StrEnum):
    THRESHOLD = "pooled_threshold.json"
    COMPLETE = "COMPLETE"


class CentralizedDecisionRule(StrEnum):
    SCORE_STRICTLY_GREATER_THAN_THRESHOLD = "score_strictly_greater_than_threshold"


class CentralizedEvaluationPublicationAsset(StrEnum):
    EVALUATION = "centralized_evaluation.json"
    COMPLETE = "COMPLETE"


CENTRALIZED_POOLED_QUANTILE_PROTOCOL = CentralizedQuantileProtocol(
    method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
    quantile=CANONICAL_QUANTILE,
)

CENTRALIZED_POOLED_METRICS = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
    MetricId.POOLED_MACRO_F1,
)


@dataclass(frozen=True, slots=True)
class CentralizedCalibrationScoreBinding:
    coordinate: CentralizedTrainingCoordinate
    partition_role: PartitionRole
    score_artifact_checksum: Checksum
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum


@dataclass(frozen=True, slots=True)
class PooledThresholdResult:
    coordinate: CentralizedTrainingCoordinate
    method: CentralizedThresholdMethod
    quantile: Quantile
    quantile_interpolation: QuantileInterpolationSemantics
    threshold: ThresholdValue
    calibration_score_count: RowCount
    score_artifact_checksum: Checksum
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    score_coordinate_checksum: Checksum

    def __post_init__(self) -> None:
        if self.method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
            raise ScientificContractError(
                "centralized threshold method must be POOLED_BENIGN_QUANTILE",
                subject=self.method,
            )
        if self.calibration_score_count < 1:
            raise ValueError("pooled threshold requires at least one benign calibration score")


@dataclass(frozen=True, slots=True)
class CentralizedThresholdPublicationRequest:
    coordinate: CentralizedTrainingCoordinate
    calibration_scores: PooledScoreArtifact
    protocol: CentralizedQuantileProtocol


class PooledThresholdDocument(StrictModel):
    method: CentralizedThresholdMethod
    quantile: Quantile
    quantile_interpolation: QuantileInterpolationSemantics
    threshold: ThresholdValue
    calibration_score_count: RowCount
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    score_artifact_checksum: Checksum

    @classmethod
    def from_result(cls, result: PooledThresholdResult) -> "PooledThresholdDocument":
        return cls(
            method=result.method,
            quantile=result.quantile,
            quantile_interpolation=result.quantile_interpolation,
            threshold=result.threshold,
            calibration_score_count=result.calibration_score_count,
            checkpoint_round=result.checkpoint_round,
            checkpoint_checksum=result.checkpoint_checksum,
            score_artifact_checksum=result.score_artifact_checksum,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCentralizedThresholdRequest:
    coordinate: CentralizedTrainingCoordinate
    calibration_scores: PooledScoreArtifact
    output_directory: Path
    protocol: CentralizedQuantileProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCentralizedThresholdResult:
    publication_status: PublicationStatus
    threshold: PooledThresholdResult
    complete_digest: Checksum


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
    publication_status: PublicationStatus
    evaluation: CentralizedEvaluationResult
    complete_digest: Checksum


def construct_centralized_threshold(
    request: ConstructCentralizedThresholdRequest,
) -> ConstructCentralizedThresholdResult:
    publication_request = CentralizedThresholdPublicationRequest(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_threshold,
                validator=centralized_threshold_is_reusable,
                loader=load_reused_centralized_threshold,
                rebaser=rebase_centralized_threshold,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructCentralizedThresholdResult(
        publication_status=publication.status,
        threshold=publication.value,
        complete_digest=publication.complete_digest,
    )


def construct_pooled_benign_quantile(
    *,
    coordinate: CentralizedTrainingCoordinate,
    calibration_scores: PooledScoreArtifact,
    protocol: CentralizedQuantileProtocol,
) -> PooledThresholdResult:
    _validate_threshold_inputs(coordinate, calibration_scores, protocol)
    scores = _benign_calibration_scores(calibration_scores)
    threshold = exact_pooled_quantile(scores, protocol.quantile)
    score_coordinate_checksum = canonical_checksum(
        CentralizedCalibrationScoreBinding(
            coordinate=calibration_scores.coordinate,
            partition_role=calibration_scores.partition_role,
            score_artifact_checksum=calibration_scores.checksum,
            checkpoint_round=calibration_scores.checkpoint_round,
            checkpoint_checksum=calibration_scores.checkpoint_checksum,
        )
    )
    return PooledThresholdResult(
        coordinate=coordinate,
        method=protocol.method,
        quantile=protocol.quantile,
        quantile_interpolation=QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR,
        threshold=threshold,
        calibration_score_count=RowCount(int(scores.size)),
        score_artifact_checksum=calibration_scores.checksum,
        checkpoint_round=calibration_scores.checkpoint_round,
        checkpoint_checksum=calibration_scores.checkpoint_checksum,
        score_coordinate_checksum=score_coordinate_checksum,
    )


def write_centralized_threshold(
    request: CentralizedThresholdPublicationRequest,
    directory: Path,
) -> PooledThresholdResult:
    result = construct_centralized_threshold_value(request)
    write_threshold_document(result, directory)
    (directory / CentralizedThresholdAssetName.COMPLETE).write_text(
        threshold_result_checksum(result).value,
        encoding="utf-8",
    )
    return result


def centralized_threshold_is_reusable(
    request: CentralizedThresholdPublicationRequest,
    directory: Path,
) -> bool:
    complete = directory / CentralizedThresholdAssetName.COMPLETE
    document = directory / CentralizedThresholdAssetName.THRESHOLD
    if not complete.is_file() or not document.is_file():
        return False
    expected = threshold_result_checksum(construct_centralized_threshold_value(request))
    try:
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except OSError:
        return False


def load_reused_centralized_threshold(
    request: CentralizedThresholdPublicationRequest,
    directory: Path,
) -> PooledThresholdResult:
    del directory
    return construct_centralized_threshold_value(request)


def rebase_centralized_threshold(
    result: PooledThresholdResult,
    directory: Path,
) -> PooledThresholdResult:
    del directory
    return result


def construct_centralized_threshold_value(
    request: CentralizedThresholdPublicationRequest,
) -> PooledThresholdResult:
    return construct_pooled_benign_quantile(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )


def exact_pooled_quantile(scores: np.ndarray, quantile: Quantile) -> ThresholdValue:
    if scores.ndim != 1 or scores.size == 0:
        raise ScientificContractError(
            "quantile requires a non-empty one-dimensional score array",
            subject=ContractSubject.SCORES,
        )
    value = float(np.quantile(scores, quantile.value, method="linear"))
    if not np.isfinite(value):
        raise ScientificContractError(
            "quantile result must be finite",
            subject=ContractSubject.THRESHOLD,
        )
    return ThresholdValue(value)


def reject_attack_rows_in_benign_calibration(
    labels: OutcomeLabelSequence,
    benign_label: PopulationOutcomeLabel,
) -> None:
    reject_non_benign_labels(
        labels,
        message="attack-labelled rows cannot enter centralized benign calibration",
        subject=ContractSubject.LABEL,
        benign_label=benign_label.value,
    )


def reject_federated_scores_for_centralized_threshold(
    identity: str,
    method: FederatedThresholdMethod,
) -> None:
    raise LeakageError(
        f"federated score artifact '{identity}' (method={method.value}) "
        "cannot enter centralized threshold construction",
        subject=ContractSubject.ARTIFACT_PATH,
    )


def reject_local_quantile_mean_as_centralized(local_quantiles: Sequence[float]) -> None:
    raise LeakageError(
        "arithmetic mean of local quantiles is the shared federated construction, not the centralized pooled quantile "
        f"(received {len(local_quantiles)} local quantile values)",
        subject=ContractSubject.LOCAL_QUANTILE_MEAN,
    )


def reject_federated_threshold_method_as_centralized(method: FederatedThresholdMethod) -> None:
    raise LeakageError(
        "federated threshold methods cannot be relabelled as the centralized pooled quantile",
        subject=method,
    )


def reject_centralized_threshold_in_federated_dispatch(method: CentralizedThresholdMethod) -> None:
    raise LeakageError(
        "centralized pooled quantile cannot enter federated threshold dispatch",
        subject=method,
    )


def write_threshold_document(result: PooledThresholdResult, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CentralizedThresholdAssetName.THRESHOLD
    path.write_text(canonical_json_text(PooledThresholdDocument.from_result(result)), encoding="utf-8")
    return path


def threshold_result_checksum(result: PooledThresholdResult) -> Checksum:
    return canonical_checksum(result)


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


def _validate_threshold_inputs(
    coordinate: CentralizedTrainingCoordinate,
    calibration_scores: PooledScoreArtifact,
    protocol: CentralizedQuantileProtocol,
) -> None:
    if protocol.method is not CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE:
        raise ScientificContractError(
            "centralized threshold protocol must declare POOLED_BENIGN_QUANTILE",
            subject=protocol.method,
        )
    if calibration_scores.coordinate != coordinate:
        raise ScientificContractError(
            "score coordinate mismatch during threshold construction",
            subject=ContractSubject.COORDINATE,
        )
    if calibration_scores.partition_role is not PartitionRole.CALIBRATION:
        raise ScientificContractError(
            "centralized threshold construction requires calibration scores",
            subject=calibration_scores.partition_role,
        )


def _benign_calibration_scores(calibration_scores: PooledScoreArtifact) -> np.ndarray:
    frame = load_score_frame(calibration_scores)
    labels = OutcomeLabelSequence(
        tuple(OutcomeLabel(str(value)) for value in frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list())
    )
    reject_attack_rows_in_benign_calibration(labels, PopulationOutcomeLabel.BENIGN)
    scores = np.asarray(
        frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list(),
        dtype=np.float64,
    )
    if scores.size == 0:
        raise ScientificContractError(
            "benign calibration score set is empty",
            subject=ContractSubject.CALIBRATION,
        )
    reject_non_finite_scores(
        scores,
        message="calibration scores must be finite",
        subject=ContractSubject.CALIBRATION,
    )
    return scores


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
    auc = (positive_rank_sum - positive_count * (positive_count + ONE_BASED_RANK_OFFSET) / MANN_WHITNEY_PAIR_FACTOR) / (
        positive_count * negative_count
    )
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
