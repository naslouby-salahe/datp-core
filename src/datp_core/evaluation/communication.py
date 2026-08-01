"""Exact logical serialized-payload accounting for threshold communication."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import MetricId, WarningCode
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import ByteCount, Seed
from datp_core.evaluation.metric_semantics import available
from datp_core.evaluation.models import CommunicationResult
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


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
    logical_element_count: int

    def __post_init__(self) -> None:
        if self.logical_element_count < 1:
            raise ScientificContractError("a communication payload requires at least one logical element")


@dataclass(frozen=True, slots=True)
class CommunicationMessageDiagnostic:
    """One directed serialized-message estimate at an exact evaluation coordinate."""

    training_seed: Seed
    coordinate: FederatedTrainingCoordinate
    sender: str
    receiver: str
    direction: MessageDirection
    payload_kind: ThresholdPayloadKind
    payload: SerializedPayloadEvidence
    client: ClientIdentity | None
    group_identity: str | None
    estimation_basis: WarningCode

    def __post_init__(self) -> None:
        if not self.sender.strip() or not self.receiver.strip() or self.sender == self.receiver:
            raise ScientificContractError(
                "communication records require distinct non-empty sender and receiver identities"
            )
        if self.coordinate.training_seed != self.training_seed:
            raise ScientificContractError("communication coordinate must match training seed")
        if self.group_identity is not None and not self.group_identity.strip():
            raise ScientificContractError("grouped communication identity must be non-empty when declared")
        if self.estimation_basis is not WarningCode.SERIALIZED_MESSAGE_SIZE_ESTIMATE:
            raise ScientificContractError("communication diagnostics require serialized-size estimate evidence")

    @property
    def estimated_serialized_bytes(self) -> ByteCount:
        return ByteCount(len(self.payload.serialized_bytes))


@dataclass(frozen=True, slots=True)
class CommunicationDiagnostic:
    """Complete estimated serialized payload accounting for one evaluation cell."""

    training_seed: Seed
    coordinate: FederatedTrainingCoordinate
    messages: tuple[CommunicationMessageDiagnostic, ...]
    total_logical_element_count: int
    total_estimated_serialized_bytes: ByteCount
    result: CommunicationResult

    def __post_init__(self) -> None:
        if not self.messages:
            raise ScientificContractError("communication diagnostics require at least one message")
        if any(message.training_seed != self.training_seed for message in self.messages):
            raise ScientificContractError("communication messages must share their training seed")
        if self.coordinate.training_seed != self.training_seed or any(
            message.coordinate != self.coordinate for message in self.messages
        ):
            raise ScientificContractError("communication messages must share their full training coordinate")
        expected_elements = sum(message.payload.logical_element_count for message in self.messages)
        expected_bytes = sum(message.estimated_serialized_bytes.value for message in self.messages)
        if (
            self.total_logical_element_count != expected_elements
            or self.total_estimated_serialized_bytes.value != expected_bytes
        ):
            raise ScientificContractError("communication totals must equal exact message payload totals")
        if self.result.estimated_serialized_bytes.value is None:
            raise ScientificContractError("communication payload bytes must be available when messages exist")


def summarize_communication(
    training_seed: Seed,
    coordinate: FederatedTrainingCoordinate,
    messages: tuple[CommunicationMessageDiagnostic, ...],
) -> CommunicationDiagnostic:
    """Return exact payload totals; values are serialized-size estimates, not network measurements."""
    return CommunicationDiagnostic(
        training_seed=training_seed,
        coordinate=coordinate,
        messages=messages,
        total_logical_element_count=sum(message.payload.logical_element_count for message in messages),
        total_estimated_serialized_bytes=ByteCount(
            sum(message.estimated_serialized_bytes.value for message in messages)
        ),
        result=CommunicationResult(
            estimated_serialized_bytes=available(
                MetricId.COMMUNICATION_BYTES,
                float(sum(message.estimated_serialized_bytes.value for message in messages)),
            )
        ),
    )
