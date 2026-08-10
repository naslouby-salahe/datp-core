from tests.unit.thresholding.helpers import client_scores

from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import Quantile, ShrinkageWeight
from datp_core.thresholds.protocols import FixedShrinkageProtocol
from datp_core.thresholds.variants.shrinkage import construct_fixed_shrinkage


def test_fixed_weight_zero_reproduces_the_shared_threshold() -> None:
    results = construct_fixed_shrinkage(
        (
            client_scores("client_a", tuple(float(value) for value in range(100))),
            client_scores("client_b", tuple(float(value + 10) for value in range(100))),
        ),
        FixedShrinkageProtocol(
            method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
            weights=(ShrinkageWeight(0.0), ShrinkageWeight(1.0)),
        ),
        Quantile(0.95),
    )

    shared, local = results.points
    assert all(assignment.threshold == shared.shared_threshold for assignment in shared.assignments)
    assert all(assignment.threshold == assignment.local_quantile.value for assignment in local.assignments)


def test_fixed_shrinkage_assignments_follow_the_declared_convex_combination() -> None:
    result = construct_fixed_shrinkage(
        (
            client_scores("client_a", tuple(float(value) for value in range(100))),
            client_scores("client_b", tuple(float(value + 10) for value in range(100))),
        ),
        FixedShrinkageProtocol(
            method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
            weights=(ShrinkageWeight(0.25),),
        ),
        Quantile(0.95),
    ).points[0]

    for assignment in result.assignments:
        expected = (
            result.weight.value * assignment.local_quantile.value.value
            + (1.0 - result.weight.value) * result.shared_threshold.value
        )
        assert assignment.threshold.value == expected
