"""Pooled centralized threshold construction and held-out evaluation."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

import numpy as np

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.datasets.partitioning.integrity import reject_non_benign_labels
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
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
from datp_core.domain.values.identifiers import OutcomeLabel, OutcomeLabelSequence, StableRowId
from datp_core.domain.values.ratios import Quantile, ScoreValue, ThresholdValue
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.confusion import calculate_confusion_counts
from datp_core.evaluation.models import ConfusionCounts, MetricAvailability
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
        if self.calibration_score_count.value < 1:
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
class CentralizedEvaluationResult:
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: ConfusionCounts
    metrics: tuple[MetricAvailability, ...]
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
        if not self.confusion.attack_assignment_valid:
            raise ScientificContractError(
                "centralized pooled evaluation always carries a valid attack assignment",
                subject=ContractSubject.ATTACK_LABELS,
            )
        if tuple(record.metric for record in self.metrics) != CENTRALIZED_POOLED_METRICS:
            raise ScientificContractError(
                "centralized evaluation metrics must follow the declared pooled metric order",
                subject=ContractSubject.METRICS,
            )


class CentralizedEvaluationDocument(StrictModel):
    coordinate: CentralizedTrainingCoordinate
    threshold_method: CentralizedThresholdMethod
    decision_rule: CentralizedDecisionRule
    threshold: ThresholdValue
    confusion: ConfusionCounts
    evaluation_row_count: RowCount
    evidence_role: EvidenceRole
    score_artifact_checksum: Checksum
    threshold_checksum: Checksum
    metrics: tuple[MetricAvailability, ...]

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
            metrics=result.metrics,
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
    row_ids, labels, scores = _evaluation_arrays(evaluation_scores)
    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=row_ids,
        threshold=threshold_result.threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=True,
    )
    metrics = _pooled_metrics(confusion=confusion, scores=scores, labels=labels)
    return CentralizedEvaluationResult(
        coordinate=coordinate,
        threshold_method=threshold_result.method,
        decision_rule=CentralizedDecisionRule.SCORE_STRICTLY_GREATER_THAN_THRESHOLD,
        threshold=threshold_result.threshold,
        confusion=confusion,
        metrics=metrics,
        evaluation_row_count=confusion.evaluation_row_count,
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


def _evaluation_arrays(
    evaluation_scores: PooledScoreArtifact,
) -> tuple[tuple[StableRowId, ...], tuple[PopulationOutcomeLabel, ...], tuple[ScoreValue, ...]]:
    frame = load_score_frame(evaluation_scores)
    row_ids = tuple(
        StableRowId(str(value)) for value in frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).to_list()
    )
    labels = tuple(
        PopulationOutcomeLabel(str(value)) for value in frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list()
    )
    scores = tuple(
        ScoreValue(float(value)) for value in frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list()
    )
    if len(scores) != len(labels) or len(scores) != len(row_ids):
        raise ScientificContractError("evaluation scores and labels must align", subject=ContractSubject.ROWS)
    return row_ids, labels, scores


def _pooled_metrics(
    *,
    confusion: ConfusionCounts,
    scores: Sequence[ScoreValue],
    labels: Sequence[PopulationOutcomeLabel],
) -> tuple[MetricAvailability, ...]:
    """Reuse the canonical per-client formulas; a pooled evaluation is one virtual client."""
    client_style_metrics = calculate_client_metrics(confusion=confusion, scores=scores, labels=labels)
    binary_macro_f1 = next(item for item in client_style_metrics if item.metric is MetricId.BINARY_MACRO_F1)
    pooled_macro_f1 = replace(binary_macro_f1, metric=MetricId.POOLED_MACRO_F1)
    return (*client_style_metrics, pooled_macro_f1)
