"""`LOCAL_THRESHOLD`: each eligible client keeps its own benign calibration quantile."""

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.protocols.models import QuantileProtocol
from datp_core.thresholding.models import LocalThresholdResult, ThresholdAssignment
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores, local_quantile


def construct_local_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> LocalThresholdResult:
    if protocol.method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
        raise ScientificContractError(
            "local threshold construction requires the LOCAL_THRESHOLD protocol", subject=protocol.method
        )
    if not eligible:
        raise ScientificContractError(
            "local threshold construction requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    assignments = tuple(ThresholdAssignment(item.client, item.value) for item in local_quantiles)
    return LocalThresholdResult(
        coordinate=eligible[0].coordinate,
        local_quantiles=local_quantiles,
        assignments=assignments,
    )
