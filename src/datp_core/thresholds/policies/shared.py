"""Shared threshold constructions and result contracts."""

from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from datp_core.artifacts.provenance import Checksum, checksum_text
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
    require_contract,
)
from datp_core.core.identifiers import AvailabilityStatus, ContractSubject, FederatedThresholdMethod
from datp_core.core.numeric import (
    CalibrationSampleWeights,
    NormalizedWeight,
    Quantile,
    RowCount,
    ThresholdValue,
    floats_exactly_equal,
)
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    LocalQuantile,
    ThresholdAssignment,
    ThresholdDiagnostic,
    mean_local_threshold,
    require_unique_clients,
    validate_assignments,
    validate_local_quantiles,
    validate_normalized_weights,
)
from datp_core.thresholds.protocols import QuantileProtocol
from datp_core.thresholds.quantiles import (
    ClientBenignCalibrationScores,
    exact_empirical_quantile,
    local_quantile,
    quantile_interpolation_semantics,
    require_eligible_cohort,
    sample_weighted_mean,
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
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
        )
        validate_assignments(
            self.assignments,
            tuple(
                ThresholdAssignment(item.client, self.shared_threshold) for item in self.contributing_local_quantiles
            ),
            label="threshold assignments",
            mismatch_message="every shared threshold assignment must carry the identical shared value",
        )
        require_contract(
            floats_exactly_equal(
                self.shared_threshold.value,
                mean_local_threshold(self.contributing_local_quantiles).value,
            ),
            ErrorMessage("shared_threshold must equal the unweighted mean of contributing local quantiles"),
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
            ErrorMessage("pooled shared quantile requires at least one pooled benign score"),
            ContractSubject.CALIBRATION,
        )
        require_unique_clients(tuple(item.client for item in self.assignments), "pooled shared quantile assignments")
        require_contract(
            bool(self.assignments),
            ErrorMessage("a shared threshold result requires at least one client assignment"),
            ContractSubject.THRESHOLD,
        )
        require_contract(
            all(floats_exactly_equal(item.threshold.value, self.shared_threshold.value) for item in self.assignments),
            ErrorMessage("every pooled shared assignment must carry the identical shared value"),
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class SampleWeightedSharedThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    contributing_local_quantiles: tuple[LocalQuantile, ...]
    normalized_weights: tuple[NormalizedWeight, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD

    def __post_init__(self) -> None:
        validate_normalized_weights(self.normalized_weights, self.contributing_local_quantiles)
        validate_local_quantiles(
            self.contributing_local_quantiles,
            self.coordinate,
            method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        )
        validate_assignments(
            self.assignments,
            tuple(
                ThresholdAssignment(item.client, self.shared_threshold) for item in self.contributing_local_quantiles
            ),
            label="threshold assignments",
            mismatch_message="every sample-weighted shared assignment must carry the identical shared value",
        )
        expected = sum(
            item.value.value * weight.value
            for item, weight in zip(self.contributing_local_quantiles, self.normalized_weights, strict=True)
        )
        require_contract(
            floats_exactly_equal(self.shared_threshold.value, expected),
            ErrorMessage("shared_threshold must equal the declared normalized weighted mean"),
            ContractSubject.THRESHOLD,
        )


def construct_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> SharedThresholdResult:
    if protocol.method is not FederatedThresholdMethod.SHARED_THRESHOLD:
        raise ScientificContractError(
            ErrorMessage("shared threshold construction requires the SHARED_THRESHOLD protocol"),
            subject=protocol.method,
        )
    require_eligible_cohort(eligible, "shared threshold construction")
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    shared_value = mean_local_threshold(local_quantiles)
    return SharedThresholdResult(
        coordinate=eligible[0].coordinate,
        quantile=protocol.quantile,
        contributing_local_quantiles=local_quantiles,
        shared_threshold=shared_value,
        assignments=tuple(ThresholdAssignment(item.client, shared_value) for item in local_quantiles),
    )


def construct_pooled_shared_quantile(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> PooledSharedQuantileResult:
    if protocol.method is not FederatedThresholdMethod.POOLED_SHARED_QUANTILE:
        raise ScientificContractError(
            ErrorMessage("pooled shared quantile construction requires the POOLED_SHARED_QUANTILE protocol"),
            subject=protocol.method,
        )
    require_eligible_cohort(eligible, "pooled shared quantile construction")
    pooled_scores = tuple(score for client_scores in eligible for score in client_scores.scores)
    shared_value = exact_empirical_quantile(
        np.asarray(tuple(score.value for score in pooled_scores), dtype=np.float64),
        protocol.quantile,
    )
    diagnostic = ThresholdDiagnostic(
        quantile_interpolation=quantile_interpolation_semantics(),
        score_set_checksum=_require_common_score_set_checksum(eligible),
        calibration_manifest_checksum=_pooled_calibration_manifest_checksum(eligible),
        tie_count=RowCount(0),
        availability=AvailabilityStatus.AVAILABLE,
    )
    return PooledSharedQuantileResult(
        coordinate=eligible[0].coordinate,
        quantile=protocol.quantile,
        pooled_benign_score_count=RowCount(len(pooled_scores)),
        diagnostic=diagnostic,
        shared_threshold=shared_value,
        assignments=tuple(ThresholdAssignment(item.client, shared_value) for item in eligible),
    )


def construct_sample_weighted_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> SampleWeightedSharedThresholdResult:
    if protocol.method is not FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD:
        raise ScientificContractError(
            ErrorMessage("sample-weighted construction requires the SAMPLE_WEIGHTED_SHARED_THRESHOLD protocol"),
            subject=protocol.method,
        )
    require_eligible_cohort(eligible, "sample-weighted shared threshold construction")
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    weights = CalibrationSampleWeights(tuple(item.calibration_count for item in local_quantiles))
    shared_value = sample_weighted_mean(tuple(item.value for item in local_quantiles), weights)
    return SampleWeightedSharedThresholdResult(
        coordinate=eligible[0].coordinate,
        quantile=protocol.quantile,
        contributing_local_quantiles=local_quantiles,
        normalized_weights=weights.normalized,
        shared_threshold=shared_value,
        assignments=tuple(ThresholdAssignment(item.client, shared_value) for item in local_quantiles),
    )


def _require_common_score_set_checksum(eligible: tuple[ClientBenignCalibrationScores, ...]) -> Checksum:
    checksums = frozenset(item.score_set_checksum for item in eligible)
    if len(checksums) != 1:
        raise ScientificContractError(
            ErrorMessage("pooled shared quantile construction requires one common score-set checksum"),
            subject=ContractSubject.SCORES,
        )
    return next(iter(checksums))


def _pooled_calibration_manifest_checksum(eligible: tuple[ClientBenignCalibrationScores, ...]) -> Checksum:
    ordered = sorted(eligible, key=lambda item: item.client)
    return checksum_text(
        "|".join(f"{item.client.client_id}:{item.calibration_manifest_checksum.value}" for item in ordered)
    )
