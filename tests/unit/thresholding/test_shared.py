import pytest
from tests.unit.thresholding.helpers import client_scores

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import Quantile
from datp_core.thresholds.policies.local import construct_local_threshold
from datp_core.thresholds.policies.shared import (
    construct_pooled_shared_quantile,
    construct_sample_weighted_shared_threshold,
    construct_shared_threshold,
)
from datp_core.thresholds.protocols import QuantileProtocol

QUANTILE = Quantile(0.5)
CLIENT_A = client_scores("client_a", (1.0, 2.0, 3.0, 4.0, 5.0))
CLIENT_B = client_scores("client_b", (10.0, 20.0, 30.0))


def test_construct_shared_threshold_is_the_unweighted_mean_of_local_quantiles() -> None:
    protocol = QuantileProtocol(
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        quantile=QUANTILE,
    )
    result = construct_shared_threshold((CLIENT_A, CLIENT_B), protocol)
    manual_mean = sum(item.value.value for item in result.contributing_local_quantiles) / len(
        result.contributing_local_quantiles
    )
    assert result.shared_threshold.value == manual_mean
    assert frozenset(assignment.client.client_id.value for assignment in result.assignments) == frozenset(
        {"client_a", "client_b"}
    )


def test_construct_shared_threshold_rejects_wrong_protocol_method() -> None:
    protocol = QuantileProtocol(
        method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        quantile=QUANTILE,
    )
    with pytest.raises(
        ScientificContractError,
        match="SHARED_THRESHOLD protocol",
    ):
        construct_shared_threshold((CLIENT_A,), protocol)


def test_shared_and_local_construction_raise_via_the_shared_eligibility_helper() -> None:
    shared_protocol = QuantileProtocol(
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        quantile=QUANTILE,
    )
    local_protocol = QuantileProtocol(
        method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        quantile=QUANTILE,
    )
    with pytest.raises(ScientificContractError) as shared_exc:
        construct_shared_threshold((), shared_protocol)
    with pytest.raises(ScientificContractError) as local_exc:
        construct_local_threshold((), local_protocol)
    assert shared_exc.value.subject == local_exc.value.subject
    assert "eligible client" in str(shared_exc.value)
    assert "eligible client" in str(local_exc.value)


def test_construct_pooled_shared_quantile_pools_every_eligible_score() -> None:
    protocol = QuantileProtocol(
        method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        quantile=QUANTILE,
    )
    result = construct_pooled_shared_quantile((CLIENT_A, CLIENT_B), protocol)
    assert result.pooled_benign_score_count.value == 8
    assert all(assignment.threshold == result.shared_threshold for assignment in result.assignments)


def test_construct_pooled_shared_quantile_differs_from_the_mean_of_local_quantiles() -> None:
    shared = construct_shared_threshold(
        (CLIENT_A, CLIENT_B),
        QuantileProtocol(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            quantile=QUANTILE,
        ),
    )
    pooled = construct_pooled_shared_quantile(
        (CLIENT_A, CLIENT_B),
        QuantileProtocol(
            method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
            quantile=QUANTILE,
        ),
    )
    assert shared.shared_threshold.value != pooled.shared_threshold.value


def test_construct_sample_weighted_shared_threshold_weights_sum_to_one() -> None:
    result = construct_sample_weighted_shared_threshold(
        (CLIENT_A, CLIENT_B),
        QuantileProtocol(
            method=(FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD),
            quantile=QUANTILE,
        ),
    )
    assert abs(sum(weight.value for weight in result.normalized_weights) - 1.0) < 1e-12


def test_construct_sample_weighted_shared_threshold_matches_manual_weighted_mean() -> None:
    result = construct_sample_weighted_shared_threshold(
        (CLIENT_A, CLIENT_B),
        QuantileProtocol(
            method=(FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD),
            quantile=QUANTILE,
        ),
    )
    manual = sum(item.value.value * item.calibration_count.value for item in result.contributing_local_quantiles) / sum(
        item.calibration_count.value for item in result.contributing_local_quantiles
    )
    assert result.shared_threshold.value == manual
