"""`LOCAL_CONFORMAL_THRESHOLD`: finite-sample local conformal thresholds from benign scores."""

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import RowCount, ScoreValue
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import ConformalProtocol
from datp_core.thresholding.models import ConformalAssignment, ConformalThresholdResult
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores, finite_sample_conformal_threshold


def construct_local_conformal_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: ConformalProtocol,
) -> ConformalThresholdResult:
    if not eligible:
        raise ScientificContractError(
            "local conformal construction requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    assignments: list[ConformalAssignment] = []
    unavailable: list[ClientIdentity] = []
    for client_scores in sorted(eligible, key=lambda item: item.client.client_id):
        try:
            threshold, rank_index, effective_quantile, tie_count = finite_sample_conformal_threshold(
                client_scores.as_array, protocol.coverage
            )
        except ScientificContractError:
            unavailable.append(client_scores.client)
            continue
        assignments.append(
            ConformalAssignment(
                client=client_scores.client,
                calibration_count=RowCount(len(client_scores.scores)),
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
        method=protocol.method,
        coordinate=eligible[0].coordinate,
        coverage=protocol.coverage,
        significance=protocol.significance,
        assignments=tuple(assignments),
        unavailable_clients=tuple(unavailable),
    )
