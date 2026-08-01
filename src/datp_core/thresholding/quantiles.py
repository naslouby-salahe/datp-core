"""The single owner of every quantile and finite-sample rank computation for federated thresholds.

Three values are operationalized here, each recorded explicitly rather than
assumed silently:

1. Empirical quantiles (local, pooled, and the cluster-fingerprint p95 feature) use
   NumPy linear interpolation (`QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR`),
   the same operationalization already locked for the independent centralized
   reference, so both branches apply one consistent rule.
2. The finite-sample local conformal rank uses the classical split-conformal rank
   correction (Vovk et al. 2005; Lei et al. 2018, Eq. 2.2):
   `rank_index = ceil((n + 1) * coverage)`, the selected value being the
   `rank_index`-th order statistic of the `n` calibration scores. When
   `rank_index > n` no finite-sample-valid threshold exists and the caller must
   report typed unavailability rather than a silent fallback quantile.
3. The federated benign-statistics matched-exceedance threshold extends the
   fixed-coefficient family (`mean + k * std`) by solving for the coefficient
   analytically under a Gaussian-tail assumption: `k = Phi^-1(quantile)`. This is
   the same summary-statistics-only family used for the fixed-coefficient
   sensitivity curve, with `k` calibrated to the quantile target instead of held
   fixed; it is not a new estimator, and callers must record the assumption.

Exact pooled-quantile computation is intentionally re-implemented here rather than
imported from `centralized_reference.thresholding`: the `thresholding-isolation`
import-linter contract forbids `datp_core.thresholding` from importing
`datp_core.centralized_reference`, keeping the two threshold-scope ladders
architecturally independent.
"""

from dataclasses import dataclass
from math import ceil, sqrt

import numpy as np
from scipy.stats import norm

from datp_core.calibration.models import CalibrationSampleReference
from datp_core.domain.enums import AvailabilityStatus, ContractSubject, QuantileInterpolationSemantics
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    CoverageTarget,
    Quantile,
    RowCount,
    SummaryCoefficient,
    ThresholdValue,
    checksum_text,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import LocalQuantile, ThresholdDiagnostic


@dataclass(frozen=True, slots=True)
class ClientBenignCalibrationScores:
    """Eligible client benign calibration scores feeding one threshold-construction cell."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    scores: tuple[float, ...]
    calibration_manifest_checksum: Checksum
    score_set_checksum: Checksum

    def __post_init__(self) -> None:
        if not self.scores:
            raise ScientificContractError(
                "eligible client calibration scores must be non-empty", subject=ContractSubject.CALIBRATION
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
    """Bind one client's benign calibration references (full set or a subsample) for construction."""
    manifest_checksum = checksum_text("|".join(sorted(reference.stable_row_id for reference in references)))
    scores = tuple(reference.score.value for reference in references)
    return ClientBenignCalibrationScores(
        client=client,
        coordinate=coordinate,
        scores=scores,
        calibration_manifest_checksum=manifest_checksum,
        score_set_checksum=score_set_checksum,
    )


def local_quantile(client_scores: ClientBenignCalibrationScores, quantile: Quantile) -> LocalQuantile:
    """Construct one client's exact empirical benign calibration quantile."""
    value = exact_empirical_quantile(client_scores.as_array, quantile)
    diagnostic = ThresholdDiagnostic(
        quantile_interpolation=quantile_interpolation_semantics(),
        score_set_checksum=client_scores.score_set_checksum,
        calibration_manifest_checksum=client_scores.calibration_manifest_checksum,
        tie_count=0,
        availability=AvailabilityStatus.AVAILABLE,
    )
    return LocalQuantile(
        client=client_scores.client,
        coordinate=client_scores.coordinate,
        quantile=quantile,
        value=value,
        calibration_count=RowCount(len(client_scores.scores)),
        diagnostic=diagnostic,
    )


def _require_score_vector(scores: np.ndarray) -> None:
    if scores.ndim != 1 or scores.size == 0:
        raise ScientificContractError(
            "quantile and rank computations require a non-empty one-dimensional score array",
            subject=ContractSubject.SCORES,
        )
    if not np.isfinite(scores).all():
        raise ScientificContractError("scores must be finite", subject=ContractSubject.SCORES)


def exact_empirical_quantile(scores: np.ndarray, quantile: Quantile) -> ThresholdValue:
    """The one quantile rule shared by local, pooled, and cluster-fingerprint computations."""
    _require_score_vector(scores)
    value = float(np.quantile(scores, quantile.value, method="linear"))
    if not np.isfinite(value):
        raise ScientificContractError("quantile result must be finite", subject=ContractSubject.THRESHOLD)
    return ThresholdValue(value)


def quantile_interpolation_semantics() -> QuantileInterpolationSemantics:
    return QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR


def unweighted_mean(values: tuple[float, ...]) -> float:
    if not values:
        raise ScientificContractError(
            "an unweighted mean requires at least one contributing value", subject=ContractSubject.THRESHOLD
        )
    return sum(values) / len(values)


def sample_weighted_mean(values: tuple[float, ...], weights: tuple[float, ...]) -> float:
    if not values or len(values) != len(weights):
        raise ScientificContractError(
            "a sample-weighted mean requires one weight per contributing value", subject=ContractSubject.THRESHOLD
        )
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ScientificContractError(
            "sample-weighted mean requires positive total support", subject=ContractSubject.THRESHOLD
        )
    return sum(value * weight for value, weight in zip(values, weights, strict=True)) / total_weight


def conformal_rank_index(calibration_count: int, coverage: CoverageTarget) -> int:
    """Classical split-conformal rank correction: `ceil((n + 1) * coverage)`."""
    if calibration_count < 1:
        raise ScientificContractError(
            "conformal rank requires at least one calibration score", subject=ContractSubject.CALIBRATION
        )
    return ceil((calibration_count + 1) * coverage.value)


def finite_sample_conformal_threshold(
    scores: np.ndarray, coverage: CoverageTarget
) -> tuple[ThresholdValue, int, float, int]:
    """Return (threshold, rank_index, effective_quantile, tie_count) or raise if infeasible."""
    _require_score_vector(scores)
    calibration_count = int(scores.size)
    rank_index = conformal_rank_index(calibration_count, coverage)
    if rank_index > calibration_count:
        raise ScientificContractError(
            "finite-sample conformal rank exceeds the available calibration count",
            subject=ContractSubject.CALIBRATION,
        )
    ordered = np.sort(scores)
    selected = float(ordered[rank_index - 1])
    tie_count = int(np.count_nonzero(ordered == selected)) - 1
    effective_quantile = rank_index / calibration_count
    return ThresholdValue(selected), rank_index, effective_quantile, tie_count


def achieved_benign_exceedance(scores: np.ndarray, threshold: ThresholdValue) -> float:
    _require_score_vector(scores)
    return float(np.mean(scores > threshold.value))


def gaussian_matched_exceedance_threshold(mean: float, variance: float, quantile: Quantile) -> ThresholdValue:
    """Solve `mean + k * std` for the `k` achieving `quantile` under a Gaussian-tail assumption."""
    if variance < 0:
        raise ScientificContractError("variance must be non-negative", subject=ContractSubject.THRESHOLD)
    coefficient = float(norm.ppf(quantile.value))
    value = mean + coefficient * sqrt(variance)
    if not np.isfinite(value):
        raise ScientificContractError("matched-exceedance threshold must be finite", subject=ContractSubject.THRESHOLD)
    return ThresholdValue(value)


def fixed_coefficient_threshold(mean: float, variance: float, coefficient: SummaryCoefficient) -> ThresholdValue:
    if variance < 0:
        raise ScientificContractError("variance must be non-negative", subject=ContractSubject.THRESHOLD)
    return ThresholdValue(mean + coefficient.value * sqrt(variance))
