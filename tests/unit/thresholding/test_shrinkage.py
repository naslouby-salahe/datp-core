import pytest
from tests.unit.thresholding.helpers import client_scores

from datp_core.core.numeric import CalibrationSize, Quantile, ShrinkageWeight
from datp_core.thresholds.protocols import FIXED_SHRINKAGE_PROTOCOL, SIZE_AWARE_SHRINKAGE_PROTOCOL
from datp_core.thresholds.variants.shrinkage import (
    construct_fixed_shrinkage,
    construct_size_aware_shrinkage,
    size_aware_shrinkage_weight,
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
    zero_result = next(item for item in result.points if item.weight.value == 0.0)
    zero_assignments = zero_result.assignments
    assert zero_assignments
    assert all(item.threshold.value == item.shared_threshold.value for item in zero_assignments)


def test_fixed_shrinkage_lambda_one_reproduces_the_local_threshold_exactly() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    one_result = next(item for item in result.points if item.weight.value == 1.0)
    one_assignments = one_result.assignments
    assert one_assignments
    assert all(item.threshold.value == item.local_quantile.value.value for item in one_assignments)


def test_fixed_shrinkage_covers_the_complete_declared_curve_for_every_client() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    assert frozenset(item.weight.value for item in result.points) == frozenset(
        weight.value for weight in FIXED_SHRINKAGE_PROTOCOL.weights
    )
    assert all(len(item.assignments) == 2 for item in result.points)


def test_construct_size_aware_shrinkage_uses_exact_calibration_support() -> None:
    result = construct_size_aware_shrinkage((CLIENT_A, CLIENT_B), SIZE_AWARE_SHRINKAGE_PROTOCOL, QUANTILE)
    assignment_a = next(item for item in result.assignments if item.client == CLIENT_A.client)
    assignment_b = next(item for item in result.assignments if item.client == CLIENT_B.client)
    assert assignment_a.used_support == CalibrationSize(len(CLIENT_A.scores))
    assert assignment_b.used_support == CalibrationSize(len(CLIENT_B.scores))
    assert assignment_a.weight == ShrinkageWeight(5 / 105)
    assert assignment_b.weight == ShrinkageWeight(3 / 103)


@pytest.mark.parametrize(
    ("used_support", "expected_weight"),
    (
        (50, 50 / 150),
        (100, 100 / 200),
        (250, 250 / 350),
        (500, 500 / 600),
        (1000, 1000 / 1100),
        (5000, 5000 / 5100),
    ),
)
def test_size_aware_weight_matches_the_locked_formula(used_support: int, expected_weight: float) -> None:
    assert size_aware_shrinkage_weight(CalibrationSize(used_support), SIZE_AWARE_SHRINKAGE_PROTOCOL) == ShrinkageWeight(
        expected_weight
    )


def test_size_aware_weight_is_bounded_and_strictly_increases_with_support() -> None:
    supports = tuple(CalibrationSize(value) for value in (1, 50, 100, 250, 500, 1000, 5000))
    weights = tuple(size_aware_shrinkage_weight(item, SIZE_AWARE_SHRINKAGE_PROTOCOL) for item in supports)
    assert all(0.0 <= item.value <= 1.0 for item in weights)
    assert all(left.value < right.value for left, right in zip(weights[:-1], weights[1:], strict=True))


def test_fixed_shrinkage_curve_preserves_unique_clients_per_lambda() -> None:
    result = construct_fixed_shrinkage(
        (CLIENT_A, CLIENT_B),
        FIXED_SHRINKAGE_PROTOCOL,
        QUANTILE,
    )
    for threshold_result in result.points:
        clients = tuple(item.client for item in threshold_result.assignments)
        assert len(clients) == len(set(clients))
        assert len(clients) == 2
    local_result = next(item for item in result.points if item.weight == ShrinkageWeight(1.0))
    local_clients = tuple(item.client for item in local_result.assignments)
    assert len(local_clients) == len(set(local_clients))
    assert len(result.points) == 5
