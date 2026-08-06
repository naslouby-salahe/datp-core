"""Local threshold construction and result contract."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.calibration import QuantileProtocol
from datp_core.thresholding.assignments import (
    LocalQuantile,
    ThresholdAssignment,
    validate_assignments,
    validate_local_quantiles,
)
from datp_core.thresholding.quantiles import (
    ClientBenignCalibrationScores,
    local_quantile,
)


@dataclass(frozen=True, slots=True)
class LocalThresholdResult:
    coordinate: FederatedTrainingCoordinate
    local_quantiles: tuple[LocalQuantile, ...]
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_THRESHOLD

    def __post_init__(self) -> None:
        validate_local_quantiles(
            self.local_quantiles,
            self.coordinate,
            label="local quantiles",
        )
        validate_assignments(
            self.assignments,
            tuple(ThresholdAssignment(item.client, item.value) for item in self.local_quantiles),
            label="threshold assignments",
            mismatch_message=("a local threshold assignment must equal the client's own local quantile"),
        )


def construct_local_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> LocalThresholdResult:
    if protocol.method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
        raise ScientificContractError(
            "local threshold construction requires the LOCAL_THRESHOLD protocol",
            subject=protocol.method,
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
