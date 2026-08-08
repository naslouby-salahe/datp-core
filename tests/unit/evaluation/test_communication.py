import pytest
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.analysis.operational.communication import (
    CommunicationMessageDiagnostic,
    MessageDirection,
    SerializedPayloadEvidence,
    ThresholdPayloadKind,
    summarize_communication,
)
from datp_core.core.identifiers import CommunicationEstimationMethod
from datp_core.core.numeric import LogicalElementCount, Seed


def test_communication_totals_are_exact_serialized_byte_counts() -> None:
    coordinate = fedavg_coordinate(Seed(6))
    message = CommunicationMessageDiagnostic(
        Seed(6),
        coordinate,
        "client_a",
        "coordinator",
        MessageDirection.CLIENT_TO_COORDINATOR,
        ThresholdPayloadKind.THRESHOLD_TRANSMISSION,
        SerializedPayloadEvidence(b"abc", LogicalElementCount(1)),
        None,
        None,
        CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
    )

    result = summarize_communication(Seed(6), coordinate, (message,))

    assert result.total_estimated_serialized_bytes.value == 3
    assert result.estimated_serialized_bytes_metric.value.value == 3.0


def test_logical_element_count_rejects_zero() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        LogicalElementCount(0)
