"""Shared-construction federated threshold methods: `SHARED_THRESHOLD` and its controls."""

import numpy as np

from datp_core.domain.enums import AvailabilityStatus, ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, RowCount, ThresholdValue, checksum_text
from datp_core.protocols.models import QuantileProtocol
from datp_core.thresholding.models import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
    ThresholdAssignment,
    ThresholdDiagnostic,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    exact_empirical_quantile,
    local_quantile,
    quantile_interpolation_semantics,
    sample_weighted_mean,
    unweighted_mean,
)


def _require_eligible(eligible: tuple[ClientBenignCalibrationScores, ...]) -> None:
    if not eligible:
        raise ScientificContractError(
            "shared-construction threshold methods require at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )


def construct_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> SharedThresholdResult:
    """`SHARED_THRESHOLD`: the unweighted arithmetic mean of eligible local quantiles."""
    if protocol.method is not FederatedThresholdMethod.SHARED_THRESHOLD:
        raise ScientificContractError(
            "shared threshold construction requires the SHARED_THRESHOLD protocol", subject=protocol.method
        )
    _require_eligible(eligible)
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    shared_value = ThresholdValue(unweighted_mean(tuple(item.value.value for item in local_quantiles)))
    assignments = tuple(ThresholdAssignment(item.client, shared_value) for item in local_quantiles)
    return SharedThresholdResult(
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        coordinate=eligible[0].coordinate,
        quantile=protocol.quantile,
        contributing_local_quantiles=local_quantiles,
        shared_threshold=shared_value,
        assignments=assignments,
    )


def construct_pooled_shared_quantile(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> PooledSharedQuantileResult:
    """`POOLED_SHARED_QUANTILE`: the exact pooled benign quantile, as a centralized pooled-raw-score oracle/control."""
    if protocol.method is not FederatedThresholdMethod.POOLED_SHARED_QUANTILE:
        raise ScientificContractError(
            "pooled shared quantile construction requires the POOLED_SHARED_QUANTILE protocol",
            subject=protocol.method,
        )
    _require_eligible(eligible)
    pooled_scores = tuple(score for client_scores in eligible for score in client_scores.scores)
    coordinate = eligible[0].coordinate
    shared_value = exact_empirical_quantile(np.asarray(pooled_scores, dtype=np.float64), protocol.quantile)
    score_set_checksum = _require_common_score_set_checksum(eligible)
    calibration_manifest_checksum = _pooled_calibration_manifest_checksum(eligible)
    diagnostic = ThresholdDiagnostic(
        quantile_interpolation=quantile_interpolation_semantics(),
        score_set_checksum=score_set_checksum,
        calibration_manifest_checksum=calibration_manifest_checksum,
        tie_count=0,
        availability=AvailabilityStatus.AVAILABLE,
    )
    assignments = tuple(ThresholdAssignment(client_scores.client, shared_value) for client_scores in eligible)
    return PooledSharedQuantileResult(
        method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        coordinate=coordinate,
        quantile=protocol.quantile,
        pooled_benign_score_count=RowCount(len(pooled_scores)),
        diagnostic=diagnostic,
        shared_threshold=shared_value,
        assignments=assignments,
    )


def construct_sample_weighted_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> SampleWeightedSharedThresholdResult:
    """`SAMPLE_WEIGHTED_SHARED_THRESHOLD`: local quantiles weighted by benign calibration support."""
    if protocol.method is not FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD:
        raise ScientificContractError(
            "sample-weighted shared threshold construction requires the SAMPLE_WEIGHTED_SHARED_THRESHOLD protocol",
            subject=protocol.method,
        )
    _require_eligible(eligible)
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    counts = tuple(float(item.calibration_count.value) for item in local_quantiles)
    total = sum(counts)
    normalized_weights = tuple(count / total for count in counts)
    shared_value = ThresholdValue(sample_weighted_mean(tuple(item.value.value for item in local_quantiles), counts))
    assignments = tuple(ThresholdAssignment(item.client, shared_value) for item in local_quantiles)
    return SampleWeightedSharedThresholdResult(
        method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        coordinate=eligible[0].coordinate,
        quantile=protocol.quantile,
        contributing_local_quantiles=local_quantiles,
        normalized_weights=normalized_weights,
        shared_threshold=shared_value,
        assignments=assignments,
    )


def _require_common_score_set_checksum(eligible: tuple[ClientBenignCalibrationScores, ...]) -> Checksum:
    checksums = frozenset(client_scores.score_set_checksum for client_scores in eligible)
    if len(checksums) != 1:
        raise ScientificContractError(
            "pooled shared quantile construction requires one common score-set checksum",
            subject=ContractSubject.SCORES,
        )
    return next(iter(checksums))


def _pooled_calibration_manifest_checksum(eligible: tuple[ClientBenignCalibrationScores, ...]) -> Checksum:
    ordered = sorted(eligible, key=lambda client_scores: client_scores.client)
    payload = "|".join(
        f"{client_scores.client.client_id}:{client_scores.calibration_manifest_checksum.value}"
        for client_scores in ordered
    )
    return checksum_text(payload)
