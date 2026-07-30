"""`FEDERATED_BENIGN_STATISTICS`: benign-only summary-statistics comparator.

Denominator convention: each client's variance is the *population* variance
(`ddof=0`). This is not an arbitrary choice — the mandatory identity
`full_pooled_variance == within_client_variance + between_client_variance` (the
law of total variance) holds exactly only when each client's variance is a
population variance; a sample (`ddof=1`) variance would break that identity.

The matched-exceedance threshold is the Gaussian-tail plug-in documented in
`thresholding.quantiles.gaussian_matched_exceedance_threshold`: the same
`mean + k * std` family used for the fixed-coefficient sensitivity curve, with
`k` solved analytically for the quantile target instead of held fixed. The exact
pooled quantile is retained only as a diagnostic reference, never as the
comparator itself.
"""

import numpy as np

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import ByteCount, Quantile, RowCount
from datp_core.protocols.models import FederatedStatisticsProtocol
from datp_core.thresholding.models import (
    ClientBenignSummary,
    CommunicationPayload,
    FederatedStatisticsThresholdResult,
    FixedCoefficientResult,
    MatchedAttainmentDiagnostic,
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

_COMMUNICATED_FIELDS = ("count", "mean", "variance")


def _client_summary(client_scores: ClientBenignCalibrationScores) -> ClientBenignSummary:
    scores = client_scores.as_array
    return ClientBenignSummary(
        client=client_scores.client,
        count=RowCount(int(scores.size)),
        mean=float(np.mean(scores)),
        variance=float(np.var(scores, ddof=0)),
        benign_exceedance_count=None,
    )


def _decomposition(summaries: tuple[ClientBenignSummary, ...]) -> PooledVarianceDecomposition:
    counts = tuple(float(summary.count.value) for summary in summaries)
    total = sum(counts)
    global_mean = sum(count * summary.mean for count, summary in zip(counts, summaries, strict=True)) / total
    within = sum(count * summary.variance for count, summary in zip(counts, summaries, strict=True)) / total
    between = (
        sum(count * (summary.mean - global_mean) ** 2 for count, summary in zip(counts, summaries, strict=True)) / total
    )
    full_pooled_variance = within + between
    between_ratio = between / full_pooled_variance if full_pooled_variance > 0 else None
    return PooledVarianceDecomposition(
        global_mean=global_mean,
        within_client_variance=within,
        between_client_variance=between,
        full_pooled_variance=full_pooled_variance,
        between_ratio=between_ratio,
    )


def _serialized_payload_bytes(summaries: tuple[ClientBenignSummary, ...]) -> ByteCount:
    payload = "|".join(
        f"{summary.client.client_id}:count={summary.count.value}:mean={summary.mean}:variance={summary.variance}"
        for summary in summaries
    )
    return ByteCount(len(payload.encode("utf-8")))


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
    ordered = tuple(sorted(eligible, key=lambda item: item.client.client_id))
    summaries = tuple(_client_summary(client_scores) for client_scores in ordered)
    decomposition = _decomposition(summaries)

    matched_threshold = gaussian_matched_exceedance_threshold(
        decomposition.global_mean, decomposition.full_pooled_variance, quantile
    )
    pooled_scores = np.concatenate([client_scores.as_array for client_scores in ordered])
    exact_pooled_quantile_reference = exact_empirical_quantile(pooled_scores, quantile)

    target_exceedance = 1.0 - quantile.value
    achieved_exceedance = achieved_benign_exceedance(pooled_scores, matched_threshold)
    signed_attainment_error = achieved_exceedance - target_exceedance
    absolute_threshold_error = abs(matched_threshold.value - exact_pooled_quantile_reference.value)
    pooled_reference_value = exact_pooled_quantile_reference.value
    relative_threshold_error = (
        absolute_threshold_error / abs(pooled_reference_value) if pooled_reference_value != 0 else None
    )
    matched_diagnostic = MatchedAttainmentDiagnostic(
        target_exceedance=target_exceedance,
        achieved_exceedance=achieved_exceedance,
        signed_attainment_error=signed_attainment_error,
        absolute_attainment_error=abs(signed_attainment_error),
        absolute_threshold_error_vs_pooled_quantile=absolute_threshold_error,
        relative_threshold_error_vs_pooled_quantile=relative_threshold_error,
    )

    fixed_coefficient_curve = tuple(
        FixedCoefficientResult(
            coefficient=coefficient,
            threshold=fixed_coefficient_threshold(
                decomposition.global_mean, decomposition.full_pooled_variance, coefficient
            ),
        )
        for coefficient in protocol.coefficients
    )
    assignments = tuple(ThresholdAssignment(client_scores.client, matched_threshold) for client_scores in ordered)
    communication_payload = CommunicationPayload(
        fields=_COMMUNICATED_FIELDS, estimated_bytes=_serialized_payload_bytes(summaries)
    )
    return FederatedStatisticsThresholdResult(
        method=protocol.method,
        coordinate=ordered[0].coordinate,
        quantile=quantile,
        client_summaries=summaries,
        decomposition=decomposition,
        matched_threshold=matched_threshold,
        matched_diagnostic=matched_diagnostic,
        exact_pooled_quantile_reference=exact_pooled_quantile_reference,
        fixed_coefficient_curve=fixed_coefficient_curve,
        assignments=assignments,
        communication_payload=communication_payload,
    )
