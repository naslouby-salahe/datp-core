import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    SerializedPayloadEvidence,
    ThresholdBroadcastAccounting,
    ThresholdPayloadKind,
    ThresholdStageCommunicationDiagnostic,
    summarize_communication,
)
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import CommunicationEstimationMethod, MessageEndpoint
from datp_core.core.numeric import ByteCount, LogicalElementCount, NonNegativeIntegerValue, Seed


def test_communication_totals_are_exact_serialized_byte_counts() -> None:
    coordinate = fedavg_coordinate(Seed(6))
    message = CommunicationMessageDiagnostic(
        Seed(6),
        coordinate,
        MessageEndpoint("client_a"),
        MessageEndpoint("coordinator"),
        MessageDirection.CLIENT_TO_COORDINATOR,
        ThresholdPayloadKind.THRESHOLD_TRANSMISSION,
        SerializedPayloadEvidence(ByteCount(3), LogicalElementCount(1)),
        None,
        None,
        CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
    )

    result = summarize_communication(Seed(6), coordinate, (message,))

    assert result.total_estimated_serialized_bytes.value == 3
    assert result.estimated_serialized_bytes_metric.value.value == 3.0


def test_logical_element_count_rejects_zero() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        LogicalElementCount(0)


def test_threshold_stage_accounting_explicitly_represents_local_zero_payload() -> None:
    coordinate = fedavg_coordinate(Seed(6))

    result = ThresholdStageCommunicationDiagnostic(
        training_seed=Seed(6),
        coordinate=coordinate,
        messages=(),
        total_logical_element_count=NonNegativeIntegerValue(0),
        total_serialized_bytes=ByteCount(0),
        broadcast_accounting=ThresholdBroadcastAccounting.ONCE_PER_LOGICAL_RECIPIENT,
        communication_round_count=NonNegativeIntegerValue(0),
    )

    assert result.messages == ()


def test_threshold_stage_communication_separates_uploads_from_responses() -> None:
    coordinate = fedavg_coordinate(Seed(6))
    upload = CommunicationMessageDiagnostic(
        Seed(6), coordinate, MessageEndpoint("client_a"), MessageEndpoint("coordinator"),
        MessageDirection.CLIENT_TO_COORDINATOR, ThresholdPayloadKind.LOCAL_QUANTILE_TRANSMISSION,
        SerializedPayloadEvidence(ByteCount(13), LogicalElementCount(1)), client_identity("client_a"), None,
        CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
    )
    response = CommunicationMessageDiagnostic(
        Seed(6), coordinate, MessageEndpoint("coordinator"), MessageEndpoint("client_a"),
        MessageDirection.COORDINATOR_TO_CLIENT, ThresholdPayloadKind.THRESHOLD_TRANSMISSION,
        SerializedPayloadEvidence(ByteCount(17), LogicalElementCount(1)), client_identity("client_a"), None,
        CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
    )

    result = ThresholdStageCommunicationDiagnostic(
        training_seed=Seed(6), coordinate=coordinate, messages=(upload, response),
        total_logical_element_count=NonNegativeIntegerValue(2), total_serialized_bytes=ByteCount(30),
        broadcast_accounting=ThresholdBroadcastAccounting.ONCE_PER_LOGICAL_RECIPIENT,
        communication_round_count=NonNegativeIntegerValue(1),
    )

    assert result.total_uploaded_serialized_bytes == ByteCount(13)
    assert result.total_response_serialized_bytes == ByteCount(17)


def test_threshold_stage_rejects_rounds_without_messages() -> None:
    coordinate = fedavg_coordinate(Seed(6))
    with pytest.raises(ScientificContractError, match="without messages"):
        ThresholdStageCommunicationDiagnostic(
            training_seed=Seed(6), coordinate=coordinate, messages=(),
            total_logical_element_count=NonNegativeIntegerValue(0), total_serialized_bytes=ByteCount(0),
            broadcast_accounting=ThresholdBroadcastAccounting.ONCE_ON_WIRE,
            communication_round_count=NonNegativeIntegerValue(1),
        )
