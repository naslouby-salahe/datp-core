"""Federated benign-summary-statistics threshold comparator and diagnostics."""

import math
from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from datp_core.core.errors import ScientificContractError, require_contract
from datp_core.core.identifiers import ContractSubject, FederatedThresholdMethod
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ByteCount,
    MetricValue,
    Quantile,
    Ratio,
    RelativeThresholdError,
    RowCount,
    ScoreMoment,
    ScoreVariance,
    SummaryCoefficient,
    ThresholdValue,
    floats_exactly_equal,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    FederatedStatisticsProtocol,
    ThresholdAssignment,
    require_unique_clients,
    validate_assignments,
)
from datp_core.thresholds.quantiles import (
    ClientBenignCalibrationScores,
    achieved_benign_exceedance,
    exact_empirical_quantile,
    fixed_coefficient_threshold,
    gaussian_matched_exceedance_threshold,
)


@dataclass(frozen=True, slots=True)
class ClientBenignSummary:
    client: ClientIdentity
    count: RowCount
    mean: ScoreMoment
    variance: ScoreVariance
    benign_exceedance_count: RowCount | None

    def __post_init__(self) -> None:
        require_contract(
            self.count.value >= 1,
            "a benign summary requires at least one calibration score",
            ContractSubject.CALIBRATION,
        )
        if self.benign_exceedance_count is not None:
            require_contract(
                self.benign_exceedance_count.value <= self.count.value,
                "benign exceedance count cannot exceed calibration score count",
                ContractSubject.THRESHOLD,
            )


@dataclass(frozen=True, slots=True)
class PooledVarianceDecomposition:
    global_mean: ScoreMoment
    within_client_variance: ScoreVariance
    between_client_variance: ScoreVariance
    full_pooled_variance: ScoreVariance
    between_ratio: Ratio | None

    def __post_init__(self) -> None:
        require_contract(
            floats_exactly_equal(
                self.full_pooled_variance.value,
                self.within_client_variance.value + self.between_client_variance.value,
            ),
            "the full pooled variance must equal within-client plus between-client variance",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class CentralizedAttainmentDiagnostic:
    target_exceedance: Quantile
    achieved_exceedance: Ratio
    signed_attainment_error: MetricValue
    absolute_attainment_error: Ratio
    absolute_threshold_error_vs_pooled_quantile: AbsoluteThresholdError
    relative_threshold_error_vs_pooled_quantile: RelativeThresholdError | None

    def __post_init__(self) -> None:
        require_contract(
            floats_exactly_equal(
                self.signed_attainment_error.value,
                self.achieved_exceedance.value - self.target_exceedance.value,
            ),
            "signed attainment error must equal achieved_exceedance minus target_exceedance",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            floats_exactly_equal(
                self.absolute_attainment_error.value,
                abs(self.signed_attainment_error.value),
            ),
            "absolute attainment error must equal abs(signed_attainment_error)",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class FixedCoefficientResult:
    coefficient: SummaryCoefficient
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True)
class FederatedStatisticsThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    client_summaries: tuple[ClientBenignSummary, ...]
    decomposition: PooledVarianceDecomposition
    matched_threshold: ThresholdValue
    centralized_attainment_diagnostic: CentralizedAttainmentDiagnostic
    centralized_pooled_quantile_diagnostic: ThresholdValue
    fixed_coefficient_curve: tuple[FixedCoefficientResult, ...]
    assignments: tuple[ThresholdAssignment, ...]
    estimated_communication_bytes: ByteCount
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS

    def __post_init__(self) -> None:
        require_contract(
            bool(self.client_summaries),
            "the federated benign-statistics comparator requires at least one client summary",
            ContractSubject.THRESHOLD,
        )
        summary_clients = tuple(item.client for item in self.client_summaries)
        require_unique_clients(summary_clients, "client summaries")
        validate_assignments(
            self.assignments,
            tuple(ThresholdAssignment(client, self.matched_threshold) for client in summary_clients),
            label="threshold assignments",
            mismatch_message="every benign-statistics assignment must carry the identical shared value",
        )


def construct_federated_benign_statistics(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: FederatedStatisticsProtocol,
    quantile: Quantile,
) -> FederatedStatisticsThresholdResult:
    if not eligible:
        raise ScientificContractError(
            "the federated benign-statistics comparator requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    ordered = tuple(sorted(eligible, key=lambda item: item.client))
    summaries = tuple(_client_summary(item) for item in ordered)
    decomposition = _decomposition(summaries)
    matched_threshold = gaussian_matched_exceedance_threshold(
        decomposition.global_mean,
        decomposition.full_pooled_variance,
        quantile,
    )
    pooled_scores = np.concatenate([item.as_array for item in ordered])
    pooled_quantile = exact_empirical_quantile(pooled_scores, quantile)
    target_exceedance = Quantile(1.0 - quantile.value)
    achieved_exceedance = achieved_benign_exceedance(pooled_scores, matched_threshold)
    signed_attainment_error = achieved_exceedance.value - target_exceedance.value
    absolute_threshold_error = AbsoluteThresholdError(abs(matched_threshold.value - pooled_quantile.value))
    relative_threshold_error = _relative_threshold_error(absolute_threshold_error, pooled_quantile)
    diagnostic = CentralizedAttainmentDiagnostic(
        target_exceedance=target_exceedance,
        achieved_exceedance=achieved_exceedance,
        signed_attainment_error=MetricValue(signed_attainment_error),
        absolute_attainment_error=Ratio(abs(signed_attainment_error)),
        absolute_threshold_error_vs_pooled_quantile=absolute_threshold_error,
        relative_threshold_error_vs_pooled_quantile=(
            None if relative_threshold_error is None else RelativeThresholdError(relative_threshold_error)
        ),
    )
    fixed_coefficient_curve = tuple(
        FixedCoefficientResult(
            coefficient=coefficient,
            threshold=fixed_coefficient_threshold(
                decomposition.global_mean,
                decomposition.full_pooled_variance,
                coefficient,
            ),
        )
        for coefficient in protocol.coefficients
    )
    return FederatedStatisticsThresholdResult(
        coordinate=ordered[0].coordinate,
        quantile=quantile,
        client_summaries=summaries,
        decomposition=decomposition,
        matched_threshold=matched_threshold,
        centralized_attainment_diagnostic=diagnostic,
        centralized_pooled_quantile_diagnostic=pooled_quantile,
        fixed_coefficient_curve=fixed_coefficient_curve,
        assignments=tuple(ThresholdAssignment(item.client, matched_threshold) for item in ordered),
        estimated_communication_bytes=_communication_bytes(summaries),
    )


def _client_summary(client_scores: ClientBenignCalibrationScores) -> ClientBenignSummary:
    scores = client_scores.as_array
    return ClientBenignSummary(
        client=client_scores.client,
        count=RowCount(scores.size),
        mean=ScoreMoment(float(np.mean(scores))),
        variance=ScoreVariance(float(np.var(scores, ddof=0))),
        benign_exceedance_count=None,
    )


def _decomposition(summaries: tuple[ClientBenignSummary, ...]) -> PooledVarianceDecomposition:
    total_count = sum(item.count.value for item in summaries)
    global_mean = sum(item.count.value * item.mean.value for item in summaries) / total_count
    within = sum(item.count.value * item.variance.value for item in summaries) / total_count
    between = sum(item.count.value * (item.mean.value - global_mean) ** 2 for item in summaries) / total_count
    full = within + between
    return PooledVarianceDecomposition(
        global_mean=ScoreMoment(global_mean),
        within_client_variance=ScoreVariance(within),
        between_client_variance=ScoreVariance(between),
        full_pooled_variance=ScoreVariance(full),
        between_ratio=Ratio(between / full) if full > 0 else None,
    )


def _communication_bytes(summaries: tuple[ClientBenignSummary, ...]) -> ByteCount:
    scalar_count = sum(3 + (1 if item.benign_exceedance_count is not None else 0) for item in summaries)
    return ByteCount(scalar_count * np.dtype(np.float64).itemsize)


def _relative_threshold_error(
    absolute_error: AbsoluteThresholdError,
    pooled_quantile: ThresholdValue,
) -> float | None:
    if pooled_quantile.value == 0:
        return None
    candidate = absolute_error.value / abs(pooled_quantile.value)
    return candidate if math.isfinite(candidate) else None
