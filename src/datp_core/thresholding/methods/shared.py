"""Shared-construction threshold methods and their result contracts."""

from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from datp_core.domain.enums import (
    AvailabilityStatus,
    ContractSubject,
    FederatedThresholdMethod,
)
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values import (
    Checksum,
    Quantile,
    RowCount,
    ThresholdValue,
    checksum_text,
    floats_exactly_equal,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.models import QuantileProtocol
from datp_core.thresholding.assignments import (
    LocalQuantile,
    ThresholdAssignment,
    ThresholdDiagnostic,
    mean_local_threshold,
    require_unique_clients,
    validate_assignments,
    validate_local_quantiles,
    validate_normalized_weights,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    exact_empirical_quantile,
    local_quantile,
    quantile_interpolation_semantics,
    sample_weighted_mean,
    unweighted_mean,
)


@dataclass(frozen=True, slots=True)
class SharedThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SHARED_THRESHOLD

    def __post_init__(self) -> None:
        validate_local_quantiles(
            self.contributing_local_quantiles,
            self.coordinate,
            label="contributing local quantiles",
        )
        validate_assignments(
            self.assignments,
            tuple((item.client, self.shared_threshold) for item in self.contributing_local_quantiles),
            label="threshold assignments",
            mismatch_message=("every assignment in a shared threshold result must carry the identical shared value"),
        )
        require_contract(
            floats_exactly_equal(
                self.shared_threshold.value,
                mean_local_threshold(self.contributing_local_quantiles),
            ),
            "shared_threshold must equal the unweighted mean of contributing local quantiles",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class PooledSharedQuantileResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    pooled_benign_score_count: RowCount
    diagnostic: ThresholdDiagnostic
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.POOLED_SHARED_QUANTILE

    def __post_init__(self) -> None:
        require_contract(
            self.pooled_benign_score_count.value >= 1,
            "pooled shared quantile requires at least one pooled benign score",
            ContractSubject.CALIBRATION,
        )
        require_unique_clients(
            tuple(item.client for item in self.assignments),
            "pooled shared quantile assignments",
        )
        require_contract(
            bool(self.assignments),
            "a shared threshold result requires at least one client assignment",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            all(
                floats_exactly_equal(
                    item.threshold.value,
                    self.shared_threshold.value,
                )
                for item in self.assignments
            ),
            "every assignment in a shared threshold result must carry the identical shared value",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class SampleWeightedSharedThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    normalized_weights: tuple[float, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD

    def __post_init__(self) -> None:
        validate_normalized_weights(
            self.normalized_weights,
            len(self.contributing_local_quantiles),
        )
        validate_local_quantiles(
            self.contributing_local_quantiles,
            self.coordinate,
            label="contributing local quantiles",
        )
        validate_assignments(
            self.assignments,
            tuple((item.client, self.shared_threshold) for item in self.contributing_local_quantiles),
            label="threshold assignments",
            mismatch_message=("every assignment in a shared threshold result must carry the identical shared value"),
        )
        expected_shared = sum(
            item.value.value * weight
            for item, weight in zip(
                self.contributing_local_quantiles,
                self.normalized_weights,
                strict=True,
            )
        )
        require_contract(
            floats_exactly_equal(self.shared_threshold.value, expected_shared),
            "shared_threshold must equal the declared normalized weighted mean of contributing local quantiles",
            ContractSubject.THRESHOLD,
        )


def construct_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> SharedThresholdResult:
    if protocol.method is not FederatedThresholdMethod.SHARED_THRESHOLD:
        raise ScientificContractError(
            "shared threshold construction requires the SHARED_THRESHOLD protocol",
            subject=protocol.method,
        )
    _require_eligible(eligible)
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    shared_value = ThresholdValue(unweighted_mean(tuple(item.value.value for item in local_quantiles)))
    assignments = tuple(ThresholdAssignment(item.client, shared_value) for item in local_quantiles)
    return SharedThresholdResult(
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
    if protocol.method is not FederatedThresholdMethod.POOLED_SHARED_QUANTILE:
        raise ScientificContractError(
            "pooled shared quantile construction requires the POOLED_SHARED_QUANTILE protocol",
            subject=protocol.method,
        )
    _require_eligible(eligible)
    pooled_scores = tuple(score for client_scores in eligible for score in client_scores.scores)
    shared_value = exact_empirical_quantile(
        np.asarray(pooled_scores, dtype=np.float64),
        protocol.quantile,
    )
    diagnostic = ThresholdDiagnostic(
        quantile_interpolation=quantile_interpolation_semantics(),
        score_set_checksum=_require_common_score_set_checksum(eligible),
        calibration_manifest_checksum=(_pooled_calibration_manifest_checksum(eligible)),
        tie_count=RowCount(0),
        availability=AvailabilityStatus.AVAILABLE,
    )
    assignments = tuple(ThresholdAssignment(client_scores.client, shared_value) for client_scores in eligible)
    return PooledSharedQuantileResult(
        coordinate=eligible[0].coordinate,
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
    shared_value = ThresholdValue(
        sample_weighted_mean(
            tuple(item.value.value for item in local_quantiles),
            counts,
        )
    )
    assignments = tuple(ThresholdAssignment(item.client, shared_value) for item in local_quantiles)
    return SampleWeightedSharedThresholdResult(
        coordinate=eligible[0].coordinate,
        quantile=protocol.quantile,
        contributing_local_quantiles=local_quantiles,
        normalized_weights=normalized_weights,
        shared_threshold=shared_value,
        assignments=assignments,
    )


def _require_eligible(
    eligible: tuple[ClientBenignCalibrationScores, ...],
) -> None:
    if not eligible:
        raise ScientificContractError(
            "shared-construction threshold methods require at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )


def _require_common_score_set_checksum(
    eligible: tuple[ClientBenignCalibrationScores, ...],
) -> Checksum:
    checksums = frozenset(client_scores.score_set_checksum for client_scores in eligible)
    if len(checksums) != 1:
        raise ScientificContractError(
            "pooled shared quantile construction requires one common score-set checksum",
            subject=ContractSubject.SCORES,
        )
    return next(iter(checksums))


def _pooled_calibration_manifest_checksum(
    eligible: tuple[ClientBenignCalibrationScores, ...],
) -> Checksum:
    ordered = sorted(eligible, key=lambda item: item.client)
    payload = "|".join(f"{item.client.client_id}:{item.calibration_manifest_checksum.value}" for item in ordered)
    return checksum_text(payload)
