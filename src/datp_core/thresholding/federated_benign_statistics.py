"""`FEDERATED_BENIGN_STATISTICS`: benign-only summary-statistics comparator.

Denominator convention: each client's variance is the *population* variance
(`ddof=0`). This is not an arbitrary choice — the mandatory identity
`full_pooled_variance == within_client_variance + between_client_variance` (the
law of total variance) holds exactly only when each client's variance is a
population variance; a sample (`ddof=1`) variance would break that identity.

The matched-exceedance threshold is the Gaussian-tail plug-in documented in
`thresholding.quantiles.gaussian_matched_exceedance_threshold`: the same
`mean + k * std` family used for the fixed-coefficient sensitivity curve, with
`k` solved analytically for the quantile target instead of held fixed.

Only count, mean, and variance are federated inputs.  Both
``centralized_attainment_diagnostic`` and ``centralized_pooled_quantile_diagnostic``
are centralized oracle diagnostics computed from the full pooled raw scores —
they are never federated comparators and raw pooled scores are never communicated.
"""

import math

import numpy as np

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    AbsoluteThresholdError,
    ByteCount,
    MetricValue,
    Quantile,
    Ratio,
    RelativeThresholdError,
    RowCount,
)
from datp_core.protocols.models import FederatedStatisticsProtocol
from datp_core.thresholding.models import (
    CentralizedAttainmentDiagnostic,
    ClientBenignSummary,
    FederatedStatisticsThresholdResult,
    FixedCoefficientResult,
    PooledVarianceDecomposition,
    ThresholdAssignment,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    achieved_benign_exceedance,
    exact_empirical_quantile,
    fixed_coefficient_threshold,
    gaussian_matched_exceedance_threshold,
)


def _client_summary(client_scores: ClientBenignCalibrationScores) -> ClientBenignSummary:
    scores = client_scores.as_array
    return ClientBenignSummary(
        client=client_scores.client,
        count=RowCount(scores.size),
        mean=float(np.mean(scores)),
        variance=float(np.var(scores, ddof=0)),
        benign_exceedance_count=None,
    )


def _decomposition(summaries: tuple[ClientBenignSummary, ...]) -> PooledVarianceDecomposition:
    total_count = sum(summary.count.value for summary in summaries)
    global_mean = sum(summary.count.value * summary.mean for summary in summaries) / total_count
    within = sum(summary.count.value * summary.variance for summary in summaries) / total_count
    between = (
        sum(summary.count.value * (summary.mean - global_mean) ** 2 for summary in summaries) / total_count
    )
    full = within + between
    between_ratio = Ratio(between / full if full > 0 else 0.0)
    return PooledVarianceDecomposition(
        global_mean=global_mean,
        within_client_variance=within,
        between_client_variance=between,
        full_pooled_variance=full,
        between_ratio=between_ratio,
    )


def _communication_bytes(summaries: tuple[ClientBenignSummary, ...]) -> ByteCount:
    scalar_count = sum(
        3 + (1 if summary.benign_exceedance_count is not None else 0)
        for summary in summaries
    )
    return ByteCount(scalar_count * np.dtype(np.float64).itemsize)


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
    summaries = tuple(_client_summary(client_scores) for client_scores in ordered)
    decomposition = _decomposition(summaries)

    matched_threshold = gaussian_matched_exceedance_threshold(
        decomposition.global_mean, decomposition.full_pooled_variance, quantile
    )
    # ── centralized oracle diagnostics (pooled raw scores, never communicated) ──
    pooled_scores = np.concatenate([client_scores.as_array for client_scores in ordered])
    centralized_pooled_quantile_diagnostic = exact_empirical_quantile(pooled_scores, quantile)

    target_exceedance = Quantile(1.0 - quantile.value)
    achieved_exceedance = achieved_benign_exceedance(pooled_scores, matched_threshold)
    signed_attainment_error = achieved_exceedance.value - target_exceedance.value
    absolute_threshold_error = abs(matched_threshold.value - centralized_pooled_quantile_diagnostic.value)
    pooled_reference_value = centralized_pooled_quantile_diagnostic.value
    relative_threshold_error: float | None = None
    if pooled_reference_value != 0:
        candidate = absolute_threshold_error / abs(pooled_reference_value)
        if math.isfinite(candidate):
            relative_threshold_error = candidate
    centralized_attainment_diagnostic = CentralizedAttainmentDiagnostic(
        target_exceedance=target_exceedance,
        achieved_exceedance=achieved_exceedance,
        signed_attainment_error=MetricValue(signed_attainment_error),
        absolute_attainment_error=Ratio(abs(signed_attainment_error)),
        absolute_threshold_error_vs_pooled_quantile=AbsoluteThresholdError(absolute_threshold_error),
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
    assignments = tuple(
        ThresholdAssignment(client_scores.client, matched_threshold) for client_scores in ordered
    )
    return FederatedStatisticsThresholdResult(
        coordinate=ordered[0].coordinate,
        quantile=quantile,
        client_summaries=summaries,
        decomposition=decomposition,
        matched_threshold=matched_threshold,
        centralized_attainment_diagnostic=centralized_attainment_diagnostic,
        centralized_pooled_quantile_diagnostic=centralized_pooled_quantile_diagnostic,
        fixed_coefficient_curve=fixed_coefficient_curve,
        assignments=assignments,
        estimated_communication_bytes=_communication_bytes(summaries),
    )
