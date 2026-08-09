"""Local threshold construction and result contract."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    LocalQuantile,
    ThresholdAssignment,
    validate_assignments,
    validate_local_quantiles,
)
from datp_core.thresholds.protocols import QuantileProtocol
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, local_quantile, require_eligible_cohort


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
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        )
        validate_assignments(
            self.assignments,
            tuple(ThresholdAssignment(item.client, item.value) for item in self.local_quantiles),
            label="threshold assignments",
            mismatch_message="a local threshold assignment must equal the client's own local quantile",
        )


def construct_local_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: QuantileProtocol,
) -> LocalThresholdResult:
    if protocol.method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
        raise ScientificContractError(
            ErrorMessage("local threshold construction requires the LOCAL_THRESHOLD protocol"),
            subject=protocol.method,
        )
    require_eligible_cohort(eligible, "local threshold construction")
    local_quantiles = tuple(local_quantile(client_scores, protocol.quantile) for client_scores in eligible)
    return LocalThresholdResult(
        coordinate=eligible[0].coordinate,
        local_quantiles=local_quantiles,
        assignments=tuple(ThresholdAssignment(item.client, item.value) for item in local_quantiles),
    )
