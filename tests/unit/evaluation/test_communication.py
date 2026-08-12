import pytest
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    SerializedPayloadEvidence,
    ThresholdPayloadKind,
    ThresholdStageCommunicationDiagnostic,
    summarize_communication,
)
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
    )

    assert result.messages == ()
