import pytest
from tests.unit.thresholding.helpers import client_scores

from datp_core.domain.enums import FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Quantile
from datp_core.protocols.models import QuantileProtocol
from datp_core.thresholding.local import construct_local_threshold

QUANTILE = Quantile(0.5)
CLIENT_A = client_scores("client_a", (1.0, 2.0, 3.0, 4.0, 5.0))
CLIENT_B = client_scores("client_b", (10.0, 20.0, 30.0))


def test_construct_local_threshold_keeps_each_clients_own_quantile() -> None:
    protocol = QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=QUANTILE)
    result = construct_local_threshold((CLIENT_A, CLIENT_B), protocol)
    by_client = {assignment.client.client_id: assignment.threshold.value for assignment in result.assignments}
    assert by_client["client_a"] == 3.0
    assert by_client["client_b"] == 20.0


def test_construct_local_threshold_no_client_borrows_another_clients_value() -> None:
    protocol = QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=QUANTILE)
    result = construct_local_threshold((CLIENT_A, CLIENT_B), protocol)
    values = {assignment.threshold.value for assignment in result.assignments}
    assert len(values) == 2


def test_construct_local_threshold_rejects_wrong_protocol_method() -> None:
    protocol = QuantileProtocol(method=FederatedThresholdMethod.SHARED_THRESHOLD, quantile=QUANTILE)

    def call():
        return construct_local_threshold((CLIENT_A,), protocol)

    with pytest.raises(ScientificContractError, match="LOCAL_THRESHOLD protocol"):
        call()


def test_construct_local_threshold_requires_at_least_one_eligible_client() -> None:
    protocol = QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=QUANTILE)

    def call():
        return construct_local_threshold((), protocol)

    with pytest.raises(ScientificContractError, match="at least one eligible client"):
        call()
