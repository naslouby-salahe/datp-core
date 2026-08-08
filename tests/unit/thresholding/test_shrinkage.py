from tests.unit.thresholding.helpers import client_scores

from datp_core.core.numeric import Quantile, ShrinkageWeight
from datp_core.protocols.calibration import FIXED_SHRINKAGE_PROTOCOL
from datp_core.thresholds.contracts import ThresholdInfeasibilityReason
from datp_core.thresholds.variants.shrinkage import (
    construct_fixed_shrinkage,
    construct_size_aware_shrinkage,
)

QUANTILE = Quantile(0.5)
CLIENT_A = client_scores("client_a", (1.0, 2.0, 3.0, 4.0, 5.0))
CLIENT_B = client_scores("client_b", (10.0, 20.0, 30.0))


def test_fixed_shrinkage_lambda_zero_reproduces_the_shared_threshold_exactly() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    zero_result = next(item for item in result if item.weight.value == 0.0)
    zero_assignments = zero_result.assignments
    assert zero_assignments
    assert all(item.threshold.value == item.shared_threshold.value for item in zero_assignments)


def test_fixed_shrinkage_lambda_one_reproduces_the_local_threshold_exactly() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    one_result = next(item for item in result if item.weight.value == 1.0)
    one_assignments = one_result.assignments
    assert one_assignments
    assert all(item.threshold.value == item.local_quantile.value.value for item in one_assignments)


def test_fixed_shrinkage_covers_the_complete_declared_curve_for_every_client() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    assert frozenset(item.weight.value for item in result) == frozenset(
        weight.value for weight in FIXED_SHRINKAGE_PROTOCOL.weights
    )
    assert all(len(item.assignments) == 2 for item in result)


def test_construct_size_aware_shrinkage_is_typed_unavailability() -> None:
    result = construct_size_aware_shrinkage(CLIENT_A.coordinate)
    assert result.reason is ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED
    assert result.detail


def test_fixed_shrinkage_curve_preserves_unique_clients_per_lambda() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    for threshold_result in result:
        clients = tuple(item.client for item in threshold_result.assignments)
        assert len(clients) == len(set(clients))
        assert len(clients) == 2
    local_result = next(item for item in result if item.weight == ShrinkageWeight(1.0))
    local_clients = tuple(item.client for item in local_result.assignments)
    assert len(local_clients) == len(set(local_clients))
    assert len(result) == 5
