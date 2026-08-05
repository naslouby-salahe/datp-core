"""Federated and centralized benign-only threshold publication."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CentralizedThresholdMethod,
    ContractSubject,
    FederatedThresholdMethod,
    PartitionRole,
    PublicationStatus,
    QuantileInterpolationSemantics,
    ScoreFrameColumn,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum, canonical_json_text
from datp_core.domain.values import (
    Checksum,
    OutcomeLabel,
    OutcomeLabelSequence,
    Quantile,
    RoundNumber,
    RowCount,
    ThresholdValue,
)
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.generate_scores import PooledScoreArtifact, load_score_frame, reject_non_finite_scores
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.populations.integrity import reject_non_benign_labels
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.inference import ScoreArtifactManifest
from datp_core.protocols.models import CentralizedQuantileProtocol
from datp_core.thresholding.common import (
    FederatedThresholdAssetName,
    FederatedThresholdPublicationRequest,
    ThresholdConstructionResult,
    federated_threshold_is_reusable,
    load_reused_federated_threshold,
    rebase_federated_threshold,
    write_federated_threshold,
)
from datp_core.thresholding.dispatch import ThresholdConstructionRequest


class CentralizedThresholdAssetName(StrEnum):
    THRESHOLD = "pooled_threshold.json"
    COMPLETE = "COMPLETE"


CENTRALIZED_POOLED_QUANTILE_PROTOCOL = CentralizedQuantileProtocol(
    method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
    quantile=CANONICAL_QUANTILE,
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
    stage: PipelineStage
    publication_status: PublicationStatus
    threshold: PooledThresholdResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructFederatedThresholdsResult:
    stage: PipelineStage
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


def construct_federated_thresholds(
    request: ConstructFederatedThresholdsRequest,
) -> ConstructFederatedThresholdsResult:
    publication_request = FederatedThresholdPublicationRequest(
        request=request.request,
        temporal_provenance=request.temporal_provenance,
        temporal_score_manifest=request.temporal_score_manifest,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_threshold,
                validator=federated_threshold_is_reusable,
                loader=load_reused_federated_threshold,
                rebaser=rebase_federated_threshold,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructFederatedThresholdsResult(
        stage=PipelineStage.CONSTRUCT_THRESHOLDS,
        result=publication.value,
        publication_status=publication.status,
        complete_digest=publication.complete_digest,
        temporal_provenance=request.temporal_provenance,
    )


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
        stage=PipelineStage.CONSTRUCT_THRESHOLDS,
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
        f"federated score artifact '{identity}' (method={method.value}) cannot enter centralized threshold construction",
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
