"""Exact logical serialized-payload accounting for threshold communication."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.analysis.metrics.models import AvailableMetric
from datp_core.analysis.metrics.semantics import available
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CommunicationEstimationMethod,
    CommunicationGroupIdentity,
    MessageEndpoint,
    MetricId,
)
from datp_core.core.numeric import ByteCount, LogicalElementCount, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


class MessageDirection(StrEnum):
    CLIENT_TO_COORDINATOR = "client_to_coordinator"
    COORDINATOR_TO_CLIENT = "coordinator_to_client"


class ThresholdPayloadKind(StrEnum):
    MODEL_TRANSMISSION = "model_transmission"
    THRESHOLD_TRANSMISSION = "threshold_transmission"
    LOCAL_QUANTILE_TRANSMISSION = "local_quantile_transmission"
    GROUPED_THRESHOLD_ASSIGNMENT = "grouped_threshold_assignment"
    BENIGN_SUMMARY_STATISTICS = "benign_summary_statistics"


@dataclass(frozen=True, slots=True)
class SerializedPayloadEvidence:
    """Actual persisted or typed serialized payload bytes, never object-size estimates."""

    serialized_bytes: bytes
    logical_element_count: LogicalElementCount

    def __post_init__(self) -> None:
        if type(self.logical_element_count) is not LogicalElementCount:
            raise ScientificContractError(ErrorMessage("communication payloads require a typed logical element count"))


@dataclass(frozen=True, slots=True)
class CommunicationMessageDiagnostic:
    """One directed serialized-message estimate at an exact evaluation coordinate."""

    training_seed: Seed
    coordinate: FederatedTrainingCoordinate
    sender: MessageEndpoint
    receiver: MessageEndpoint
    direction: MessageDirection
    payload_kind: ThresholdPayloadKind
    payload: SerializedPayloadEvidence
    client: ClientIdentity | None
    group_identity: CommunicationGroupIdentity | None
    estimation_basis: CommunicationEstimationMethod

    def __post_init__(self) -> None:
        if self.sender == self.receiver:
            raise ScientificContractError(
                ErrorMessage("communication records require distinct non-empty sender and receiver identities")
            )
        if self.coordinate.training_seed != self.training_seed:
            raise ScientificContractError(ErrorMessage("communication coordinate must match training seed"))
        if self.estimation_basis is not CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE:
            raise ScientificContractError(
                ErrorMessage("communication diagnostics require serialized-size estimate evidence")
            )

    @property
    def estimated_serialized_bytes(self) -> ByteCount:
        return ByteCount(len(self.payload.serialized_bytes))


@dataclass(frozen=True, slots=True)
class CommunicationDiagnostic:
    """Complete estimated serialized payload accounting for one evaluation cell."""

    training_seed: Seed
    coordinate: FederatedTrainingCoordinate
    messages: tuple[CommunicationMessageDiagnostic, ...]
    total_logical_element_count: LogicalElementCount
    total_estimated_serialized_bytes: ByteCount

    def __post_init__(self) -> None:
        if not self.messages:
            raise ScientificContractError(ErrorMessage("communication diagnostics require at least one message"))

        if self.coordinate.training_seed != self.training_seed:
            raise ScientificContractError(
                ErrorMessage("communication messages must share their full training coordinate")
            )

        expected_elements = 0
        expected_bytes = 0

        for message in self.messages:
            if message.training_seed != self.training_seed:
                raise ScientificContractError(ErrorMessage("communication messages must share their training seed"))
            if message.coordinate != self.coordinate:
                raise ScientificContractError(
                    ErrorMessage("communication messages must share their full training coordinate")
                )

            expected_elements += message.payload.logical_element_count.value
            expected_bytes += len(message.payload.serialized_bytes)

        if (
            self.total_logical_element_count.value != expected_elements
            or self.total_estimated_serialized_bytes.value != expected_bytes
        ):
            raise ScientificContractError(ErrorMessage("communication totals must equal exact message payload totals"))

    @property
    def estimated_serialized_bytes_metric(self) -> AvailableMetric:
        return available(MetricId.COMMUNICATION_BYTES, float(self.total_estimated_serialized_bytes.value))


def summarize_communication(
    training_seed: Seed,
    coordinate: FederatedTrainingCoordinate,
    messages: tuple[CommunicationMessageDiagnostic, ...],
) -> CommunicationDiagnostic:
    """Return exact payload totals; values are serialized-size estimates, not network measurements."""
    expected_elements = 0
    expected_bytes = 0

    for message in messages:
        expected_elements += message.payload.logical_element_count.value
        expected_bytes += len(message.payload.serialized_bytes)

    return CommunicationDiagnostic(
        training_seed=training_seed,
        coordinate=coordinate,
        messages=messages,
        total_logical_element_count=LogicalElementCount(expected_elements),
        total_estimated_serialized_bytes=ByteCount(expected_bytes),
    )
