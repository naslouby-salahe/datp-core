"""Quantile and finite-sample rank computations for federated thresholds."""

from dataclasses import dataclass
from math import ceil, sqrt

import numpy as np
from scipy.stats import norm

from datp_core.calibration.models import CalibrationSampleReference
from datp_core.domain.enums import (
    AvailabilityStatus,
    ContractSubject,
    QuantileInterpolationSemantics,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    ConformalRankIndex,
    CoverageTarget,
    Quantile,
    Ratio,
    RowCount,
    SummaryCoefficient,
    ThresholdValue,
    checksum_text,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.assignments import LocalQuantile, ThresholdDiagnostic


@dataclass(frozen=True, slots=True)
class ClientBenignCalibrationScores:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    scores: tuple[float, ...]
    calibration_manifest_checksum: Checksum
    score_set_checksum: Checksum

    def __post_init__(self) -> None:
        if not self.scores:
            raise ScientificContractError(
                "eligible client calibration scores must be non-empty",
                subject=ContractSubject.CALIBRATION,
            )
        if not all(np.isfinite(score) for score in self.scores):
            raise ScientificContractError(
                "every calibration score must be finite",
                subject=ContractSubject.CALIBRATION,
            )

    @property
    def as_array(self) -> np.ndarray:
        return np.asarray(self.scores, dtype=np.float64)


def calibration_scores_from_references(
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    references: tuple[CalibrationSampleReference, ...],
    score_set_checksum: Checksum,
) -> ClientBenignCalibrationScores:
    manifest_checksum = checksum_text(
        "|".join(
            sorted(reference.stable_row_id for reference in references)
        )
    )
    return ClientBenignCalibrationScores(
        client=client,
        coordinate=coordinate,
        scores=tuple(reference.score.value for reference in references),
        calibration_manifest_checksum=manifest_checksum,
        score_set_checksum=score_set_checksum,
    )


def local_quantile(
    client_scores: ClientBenignCalibrationScores,
    quantile: Quantile,
) -> LocalQuantile:
    value = exact_empirical_quantile(client_scores.as_array, quantile)
    return LocalQuantile(
        client=client_scores.client,
        coordinate=client_scores.coordinate,
        quantile=quantile,
        value=value,
        calibration_count=RowCount(len(client_scores.scores)),
        diagnostic=ThresholdDiagnostic(
            quantile_interpolation=quantile_interpolation_semantics(),
            score_set_checksum=client_scores.score_set_checksum,
            calibration_manifest_checksum=(
                client_scores.calibration_manifest_checksum
            ),
            tie_count=RowCount(0),
            availability=AvailabilityStatus.AVAILABLE,
        ),
    )


def exact_empirical_quantile(
    scores: np.ndarray,
    quantile: Quantile,
) -> ThresholdValue:
    _require_score_vector(scores)
    value = float(np.quantile(scores, quantile.value, method="linear"))
    if not np.isfinite(value):
        raise ScientificContractError(
            "quantile result must be finite",
            subject=ContractSubject.THRESHOLD,
        )
    return ThresholdValue(value)


def quantile_interpolation_semantics() -> QuantileInterpolationSemantics:
    return QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR


def unweighted_mean(values: tuple[float, ...]) -> float:
    if not values:
        raise ScientificContractError(
            "an unweighted mean requires at least one contributing value",
            subject=ContractSubject.THRESHOLD,
        )
    return sum(values) / len(values)


def sample_weighted_mean(
    values: tuple[float, ...],
    weights: tuple[float, ...],
) -> float:
    if not values or len(values) != len(weights):
        raise ScientificContractError(
            "a sample-weighted mean requires one weight per contributing value",
            subject=ContractSubject.THRESHOLD,
        )
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ScientificContractError(
            "sample-weighted mean requires positive total support",
            subject=ContractSubject.THRESHOLD,
        )
    return sum(
        value * weight
        for value, weight in zip(values, weights, strict=True)
    ) / total_weight


def conformal_rank_index(
    calibration_count: RowCount,
    coverage: CoverageTarget,
) -> ConformalRankIndex:
    if calibration_count.value < 1:
        raise ScientificContractError(
            "conformal rank requires at least one calibration score",
            subject=ContractSubject.CALIBRATION,
        )
    return ConformalRankIndex(
        ceil((calibration_count.value + 1) * coverage.value)
    )


def finite_sample_conformal_threshold(
    scores: np.ndarray,
    coverage: CoverageTarget,
) -> tuple[ThresholdValue, ConformalRankIndex, Quantile, RowCount]:
    _require_score_vector(scores)
    calibration_count = RowCount(int(scores.size))
    rank_index = conformal_rank_index(calibration_count, coverage)
    if rank_index.value > calibration_count.value:
        raise ScientificContractError(
            "finite-sample conformal rank exceeds the available calibration count",
            subject=ContractSubject.CALIBRATION,
        )
    ordered = np.sort(scores)
    selected = float(ordered[rank_index.value - 1])
    tie_count = RowCount(int(np.count_nonzero(ordered == selected)) - 1)
    return (
        ThresholdValue(selected),
        rank_index,
        Quantile(rank_index.value / calibration_count.value),
        tie_count,
    )


def achieved_benign_exceedance(
    scores: np.ndarray,
    threshold: ThresholdValue,
) -> Ratio:
    _require_score_vector(scores)
    return Ratio(float(np.mean(scores > threshold.value)))


def gaussian_matched_exceedance_threshold(
    mean: float,
    variance: float,
    quantile: Quantile,
) -> ThresholdValue:
    if variance < 0:
        raise ScientificContractError(
            "variance must be non-negative",
            subject=ContractSubject.THRESHOLD,
        )
    value = mean + float(norm.ppf(quantile.value)) * sqrt(variance)
    if not np.isfinite(value):
        raise ScientificContractError(
            "matched-exceedance threshold must be finite",
            subject=ContractSubject.THRESHOLD,
        )
    return ThresholdValue(value)


def fixed_coefficient_threshold(
    mean: float,
    variance: float,
    coefficient: SummaryCoefficient,
) -> ThresholdValue:
    if variance < 0:
        raise ScientificContractError(
            "variance must be non-negative",
            subject=ContractSubject.THRESHOLD,
        )
    return ThresholdValue(mean + coefficient.value * sqrt(variance))


def _require_score_vector(scores: np.ndarray) -> None:
    if scores.ndim != 1 or scores.size == 0:
        raise ScientificContractError(
            "quantile and rank computations require a non-empty one-dimensional score array",
            subject=ContractSubject.SCORES,
        )
    if not np.isfinite(scores).all():
        raise ScientificContractError(
            "scores must be finite",
            subject=ContractSubject.SCORES,
        )
