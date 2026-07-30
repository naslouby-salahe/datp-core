from tests.unit.thresholding.helpers import client_scores

from datp_core.protocols.calibration import CONFORMAL_PROTOCOL
from datp_core.thresholding.conformal import construct_local_conformal_threshold

SUFFICIENT_CLIENT = client_scores("client_a", tuple(float(i) for i in range(1, 101)))
INSUFFICIENT_CLIENT = client_scores("client_b", (1.0, 2.0))


def test_construct_local_conformal_threshold_assigns_sufficient_clients() -> None:
    result = construct_local_conformal_threshold((SUFFICIENT_CLIENT,), CONFORMAL_PROTOCOL)
    assert len(result.assignments) == 1
    assert not result.unavailable_clients
    assignment = result.assignments[0]
    assert assignment.rank_index == 96
    assert assignment.threshold.value == 96.0


def test_construct_local_conformal_threshold_marks_insufficient_clients_unavailable_not_a_fallback_quantile() -> None:
    result = construct_local_conformal_threshold((SUFFICIENT_CLIENT, INSUFFICIENT_CLIENT), CONFORMAL_PROTOCOL)
    assigned_clients = {assignment.client.client_id for assignment in result.assignments}
    assert "client_a" in assigned_clients
    assert "client_b" not in assigned_clients
    assert result.unavailable_clients == (INSUFFICIENT_CLIENT.client,)
