from tests.unit.learning.federated.helpers import client_identity, ditto_coordinates

from datp_core.analysis.operational.ditto import shared_or_local_threshold_stage_communication
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import Seed


def test_ditto_shared_and_local_threshold_stage_costs_are_explicit_and_serializer_bound() -> None:
    coordinates, _ = ditto_coordinates(Seed(11))
    clients = (client_identity("client_a"), client_identity("client_b"))

    shared = shared_or_local_threshold_stage_communication(
        coordinates.personalized_coordinate,
        FederatedThresholdMethod.SHARED_THRESHOLD,
        clients,
    )
    local = shared_or_local_threshold_stage_communication(
        coordinates.personalized_coordinate,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        clients,
    )

    assert shared.total_serialized_bytes.value == 32
    assert shared.communication_round_count.value == 1
    assert local.total_serialized_bytes.value == 0
    assert local.communication_round_count.value == 0
