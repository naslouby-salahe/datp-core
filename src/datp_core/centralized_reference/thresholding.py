"""Pooled benign quantile threshold for the independent centralized reference."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np

from datp_core.centralized_reference.scoring import (
    PooledScoreArtifact,
    load_score_frame,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import (
    CentralizedThresholdMethod,
    ContractSubject,
    FederatedThresholdMethod,
    PartitionRole,
    QuantileInterpolationSemantics,
    ScoreFrameColumn,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    Checksum,
    OutcomeLabelSequence,
    Quantile,
    RoundNumber,
    ThresholdValue,
    checksum_text,
)
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.models import CentralizedQuantileProtocol


class CentralizedThresholdAssetName(StrEnum):
    THRESHOLD = "pooled_threshold.json"
    COMPLETE = "COMPLETE"


CENTRALIZED_POOLED_QUANTILE_PROTOCOL = CentralizedQuantileProtocol(
    method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
    quantile=CANONICAL_QUANTILE,
)


@dataclass(frozen=True, slots=True)
class PooledThresholdResult:
    coordinate: CentralizedTrainingCoordinate
    method: CentralizedThresholdMethod
    quantile: Quantile
    quantile_interpolation: QuantileInterpolationSemantics
    threshold: ThresholdValue
    calibration_score_count: int
    score_artifact_checksum: Checksum
    checkpoint_round: RoundNumber
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
class FederatedScoreMarker:
    """Structural marker used only to reject federated artifacts at the centralized boundary."""

    identity: str
    method: FederatedThresholdMethod


def construct_pooled_benign_quantile(
    *,
    coordinate: CentralizedTrainingCoordinate,
    calibration_scores: PooledScoreArtifact,
    protocol: CentralizedQuantileProtocol,
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN,
) -> PooledThresholdResult:
    """Construct the exact pooled benign calibration quantile threshold."""
    _validate_threshold_inputs(coordinate, calibration_scores, protocol)
    scores = _benign_calibration_scores(calibration_scores, benign_label)
    threshold = exact_pooled_quantile(scores, protocol.quantile)
    score_coordinate_checksum = checksum_text(
        f"{calibration_scores.checksum.value}|{calibration_scores.checkpoint_round.value}|"
        f"{calibration_scores.partition_role.value}"
    )
    return PooledThresholdResult(
        coordinate=coordinate,
        method=protocol.method,
        quantile=protocol.quantile,
        quantile_interpolation=QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR,
        threshold=threshold,
        calibration_score_count=int(scores.size),
        score_artifact_checksum=calibration_scores.checksum,
        checkpoint_round=calibration_scores.checkpoint_round,
        score_coordinate_checksum=score_coordinate_checksum,
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
            "score coordinate mismatch during threshold construction", subject=ContractSubject.COORDINATE
        )
    if calibration_scores.partition_role is not PartitionRole.CALIBRATION:
        raise ScientificContractError(
            "centralized threshold construction requires calibration scores",
            subject=calibration_scores.partition_role,
        )


def _benign_calibration_scores(
    calibration_scores: PooledScoreArtifact, benign_label: PopulationOutcomeLabel
) -> np.ndarray:
    frame = load_score_frame(calibration_scores)
    labels = OutcomeLabelSequence(
        tuple(str(value) for value in frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list())
    )
    reject_attack_rows_in_benign_calibration(labels, benign_label)
    scores = np.asarray(
        frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list(),
        dtype=np.float64,
    )
    if scores.size == 0:
        raise ScientificContractError("benign calibration score set is empty", subject=ContractSubject.CALIBRATION)
    if not np.isfinite(scores).all():
        raise ScientificContractError("calibration scores must be finite", subject=ContractSubject.CALIBRATION)
    return scores


def exact_pooled_quantile(scores: np.ndarray, quantile: Quantile) -> ThresholdValue:
    """Exact empirical q-quantile with linear interpolation."""
    if scores.ndim != 1 or scores.size == 0:
        raise ScientificContractError(
            "quantile requires a non-empty one-dimensional score array", subject=ContractSubject.SCORES
        )
    value = float(np.quantile(scores, quantile.value, method="linear"))
    if not np.isfinite(value):
        raise ScientificContractError("quantile result must be finite", subject=ContractSubject.THRESHOLD)
    return ThresholdValue(value)


def reject_attack_rows_in_benign_calibration(
    labels: OutcomeLabelSequence, benign_label: PopulationOutcomeLabel
) -> None:
    if any(label != benign_label.value for label in labels):
        raise LeakageError(
            "attack-labelled rows cannot enter centralized benign calibration",
            subject=ContractSubject.LABEL,
        )


def reject_federated_scores_for_centralized_threshold(marker: FederatedScoreMarker) -> None:
    raise LeakageError(
        f"federated score artifact '{marker.identity}' (method={marker.method.value}) "
        "cannot enter centralized threshold construction",
        subject=ContractSubject.ARTIFACT_PATH,
    )


def reject_local_quantile_mean_as_centralized(local_quantiles: Sequence[float]) -> None:
    raise LeakageError(
        "arithmetic mean of local quantiles is the shared federated construction, not the centralized pooled "
        f"quantile (received {len(local_quantiles)} local quantile values)",
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
    payload = (
        "{\n"
        f'  "method": "{result.method.value}",\n'
        f'  "quantile": {result.quantile.value},\n'
        f'  "quantile_interpolation": "{result.quantile_interpolation.value}",\n'
        f'  "threshold": {result.threshold.value},\n'
        f'  "calibration_score_count": {result.calibration_score_count},\n'
        f'  "checkpoint_round": {result.checkpoint_round.value},\n'
        f'  "score_artifact_checksum": "{result.score_artifact_checksum.value}"\n'
        "}\n"
    )
    path.write_text(payload, encoding="utf-8")
    return path


def threshold_result_checksum(result: PooledThresholdResult) -> Checksum:
    return checksum_text(
        f"{result.method.value}|{result.quantile.value}|{result.threshold.value}|"
        f"{result.calibration_score_count}|{result.score_artifact_checksum.value}"
    )
