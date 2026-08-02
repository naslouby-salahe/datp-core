"""`LOCAL_CONFORMAL_THRESHOLD`: finite-sample local conformal thresholds from benign scores.

Coverage is derived from the request quantile: ``coverage = quantile.value`` and
``significance = 1 - quantile.value``.  A client is unavailable only when the
finite-sample conformal rank exceeds the available calibration count
(``ceil((n + 1) * coverage) > n``).  Malformed, empty, non-finite, or corrupted
score errors propagate; they are never silently converted into unavailability.
"""

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CoverageTarget, Quantile, Ratio, RowCount, ScoreValue
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import ConformalAssignment, ConformalThresholdResult
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    conformal_rank_index,
    finite_sample_conformal_threshold,
)


def construct_local_conformal_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    quantile: Quantile,
) -> ConformalThresholdResult:
    if not eligible:
        raise ScientificContractError(
            "local conformal construction requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    coverage_value = quantile.value
    coverage = CoverageTarget(coverage_value)
    significance = Ratio(1.0 - coverage_value)

    eligible_clients = tuple(item.client for item in eligible)

    assignments: list[ConformalAssignment] = []
    unavailable: list[ClientIdentity] = []
    for client_scores in sorted(eligible, key=lambda item: item.client):
        calibration_count_int = int(client_scores.as_array.size)
        rank_index = conformal_rank_index(RowCount(calibration_count_int), coverage)
        if rank_index > calibration_count_int:
            unavailable.append(client_scores.client)
            continue
        threshold, _, effective_quantile, tie_count = finite_sample_conformal_threshold(
            client_scores.as_array, coverage
        )
        assignments.append(
            ConformalAssignment(
                client=client_scores.client,
                calibration_count=RowCount(calibration_count_int),
                rank_index=rank_index,
                effective_quantile=effective_quantile,
                selected_score=ScoreValue(threshold.value),
                tie_count=tie_count,
                threshold=threshold,
            )
        )
    if not assignments:
        raise ScientificContractError(
            "no eligible client has sufficient support for the finite-sample conformal rule",
            subject=ContractSubject.CALIBRATION,
        )
    return ConformalThresholdResult(
        coordinate=eligible[0].coordinate,
        coverage=coverage,
        significance=significance,
        eligible_clients=eligible_clients,
        assignments=tuple(assignments),
        unavailable_clients=tuple(unavailable),
    )
