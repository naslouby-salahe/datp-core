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
from datp_core.core.numeric import ByteCount, LogicalElementCount, MetricValue, NonNegativeIntegerValue, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


class MessageDirection(StrEnum):
    CLIENT_TO_COORDINATOR = "client_to_coordinator"
    COORDINATOR_TO_CLIENT = "coordinator_to_client"


class ThresholdBroadcastAccounting(StrEnum):
    """How coordinator threshold responses are totalled in a threshold-stage report."""

    ONCE_ON_WIRE = "once_on_wire"
    ONCE_PER_LOGICAL_RECIPIENT = "once_per_logical_recipient"


class ThresholdPayloadKind(StrEnum):
    MODEL_TRANSMISSION = "model_transmission"
    THRESHOLD_TRANSMISSION = "threshold_transmission"
    LOCAL_QUANTILE_TRANSMISSION = "local_quantile_transmission"
    GROUPED_THRESHOLD_ASSIGNMENT = "grouped_threshold_assignment"
    CLUSTER_FINGERPRINT_TRANSMISSION = "cluster_fingerprint_transmission"
    BENIGN_SUMMARY_STATISTICS = "benign_summary_statistics"
    KLL_SKETCH_TRANSMISSION = "kll_sketch_transmission"


@dataclass(frozen=True, slots=True)
class SerializedPayloadEvidence:
    serialized_byte_count: ByteCount
    logical_element_count: LogicalElementCount

    def __post_init__(self) -> None:
        if type(self.serialized_byte_count) is not ByteCount:
            raise ScientificContractError(ErrorMessage("communication payloads require a typed serialized byte count"))
        if type(self.logical_element_count) is not LogicalElementCount:
            raise ScientificContractError(ErrorMessage("communication payloads require a typed logical element count"))


@dataclass(frozen=True, slots=True)
class CommunicationMessageDiagnostic:
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
        return self.payload.serialized_byte_count


@dataclass(frozen=True, slots=True)
class CommunicationDiagnostic:
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
            expected_bytes += message.estimated_serialized_bytes.value

        if (
            self.total_logical_element_count.value != expected_elements
            or self.total_estimated_serialized_bytes.value != expected_bytes
        ):
            raise ScientificContractError(ErrorMessage("communication totals must equal exact message payload totals"))

    @property
    def estimated_serialized_bytes_metric(self) -> AvailableMetric:
        return available(MetricId.COMMUNICATION_BYTES, MetricValue(float(self.total_estimated_serialized_bytes.value)))


@dataclass(frozen=True, slots=True)
class ThresholdStageCommunicationDiagnostic:
    """Threshold-only disclosure and transport, excluding federated model-update traffic."""

    training_seed: Seed
    coordinate: FederatedTrainingCoordinate
    messages: tuple[CommunicationMessageDiagnostic, ...]
    total_logical_element_count: NonNegativeIntegerValue
    total_serialized_bytes: ByteCount
    broadcast_accounting: ThresholdBroadcastAccounting
    communication_round_count: NonNegativeIntegerValue

    def __post_init__(self) -> None:
        expected_elements = sum(item.payload.logical_element_count.value for item in self.messages)
        expected_bytes = sum(item.estimated_serialized_bytes.value for item in self.messages)
        if self.total_logical_element_count.value != expected_elements:
            raise ScientificContractError(ErrorMessage("threshold-stage logical elements must equal message totals"))
        if self.total_serialized_bytes.value != expected_bytes:
            raise ScientificContractError(ErrorMessage("threshold-stage bytes must equal message totals"))
        if not self.messages and self.communication_round_count.value != 0:
            raise ScientificContractError(
                ErrorMessage("a threshold stage without messages cannot report communication rounds")
            )
        if self.messages and self.communication_round_count.value < 1:
            raise ScientificContractError(
                ErrorMessage("a threshold stage with messages requires one or more communication rounds")
            )
        for message in self.messages:
            if message.training_seed != self.training_seed or message.coordinate != self.coordinate:
                raise ScientificContractError(
                    ErrorMessage("threshold-stage messages must match the evaluated coordinate")
                )
            if message.payload_kind is ThresholdPayloadKind.MODEL_TRANSMISSION:
                raise ScientificContractError(
                    ErrorMessage("threshold-stage accounting cannot contain model transmission")
                )

    @property
    def upload_messages(self) -> tuple[CommunicationMessageDiagnostic, ...]:
        return tuple(item for item in self.messages if item.direction is MessageDirection.CLIENT_TO_COORDINATOR)

    @property
    def response_messages(self) -> tuple[CommunicationMessageDiagnostic, ...]:
        return tuple(item for item in self.messages if item.direction is MessageDirection.COORDINATOR_TO_CLIENT)

    @property
    def total_uploaded_serialized_bytes(self) -> ByteCount:
        return ByteCount(sum(item.estimated_serialized_bytes.value for item in self.upload_messages))

    @property
    def total_response_serialized_bytes(self) -> ByteCount:
        return ByteCount(sum(item.estimated_serialized_bytes.value for item in self.response_messages))


def summarize_communication(
    training_seed: Seed,
    coordinate: FederatedTrainingCoordinate,
    messages: tuple[CommunicationMessageDiagnostic, ...],
) -> CommunicationDiagnostic:
    expected_elements = 0
    expected_bytes = 0

    for message in messages:
        expected_elements += message.payload.logical_element_count.value
        expected_bytes += message.estimated_serialized_bytes.value

    return CommunicationDiagnostic(
        training_seed=training_seed,
        coordinate=coordinate,
        messages=messages,
        total_logical_element_count=LogicalElementCount(expected_elements),
        total_estimated_serialized_bytes=ByteCount(expected_bytes),
    )
