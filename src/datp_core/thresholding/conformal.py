"""`LOCAL_CONFORMAL_THRESHOLD`: finite-sample local conformal thresholds from benign scores.

Coverage is derived from the request quantile: ``coverage = quantile.value`` and
``significance = 1 - quantile.value``.  A client is unavailable only when the
finite-sample conformal rank exceeds the available calibration count
(``ceil((n + 1) * coverage) > n``).  Invalid, empty, non-finite, or corrupted
score errors propagate; they are never silently converted into unavailability.
"""

import numpy as np

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CoverageTarget, Quantile, Ratio, RowCount, ScoreValue, ThresholdValue
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import ConformalAssignment, ConformalThresholdResult
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    conformal_rank_index,
    _require_score_vector,
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

    assignments: list[ConformalAssignment] = []
    unavailable: list[ClientIdentity] = []
    for client_scores in sorted(eligible, key=lambda item: item.client):
        scores = client_scores.as_array
        _require_score_vector(scores)
        calibration_count_int = int(scores.size)
        rank_index = conformal_rank_index(RowCount(calibration_count_int), coverage)
        if rank_index > calibration_count_int:
            unavailable.append(client_scores.client)
            continue
        ordered = np.sort(scores)
        selected = float(ordered[rank_index - 1])
        tie_count = int(np.count_nonzero(ordered == selected)) - 1
        effective_quantile = rank_index / calibration_count_int
        assignments.append(
            ConformalAssignment(
                client=client_scores.client,
                calibration_count=RowCount(calibration_count_int),
                rank_index=rank_index,
                effective_quantile=effective_quantile,
                selected_score=ScoreValue(selected),
                tie_count=tie_count,
                threshold=ThresholdValue(selected),
            )
        )
    if not assignments:
        raise ScientificContractError(
            "no eligible client has sufficient support for the finite-sample conformal rule",
            subject=ContractSubject.CALIBRATION,
        )
    return ConformalThresholdResult(
        method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        coordinate=eligible[0].coordinate,
        coverage=coverage,
        significance=significance,
        assignments=tuple(assignments),
        unavailable_clients=tuple(unavailable),
    )
