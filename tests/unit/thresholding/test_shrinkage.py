from tests.unit.thresholding.helpers import client_scores

from datp_core.domain.values import Quantile
from datp_core.protocols.calibration import FIXED_SHRINKAGE_PROTOCOL
from datp_core.thresholding.models import ThresholdInfeasibilityReason
from datp_core.thresholding.shrinkage import construct_fixed_shrinkage, construct_size_aware_shrinkage

QUANTILE = Quantile(0.5)
CLIENT_A = client_scores("client_a", (1.0, 2.0, 3.0, 4.0, 5.0))
CLIENT_B = client_scores("client_b", (10.0, 20.0, 30.0))


def test_fixed_shrinkage_lambda_zero_reproduces_the_shared_threshold_exactly() -> None:
    result = construct_fixed_shrinkage((CLIENT_A, CLIENT_B), FIXED_SHRINKAGE_PROTOCOL, QUANTILE)
    zero_assignments = [a for a in result.assignments if a.lambda_weight.value == 0.0]
    assert zero_assignments
    for assignment in zero_assignments:
        assert assignment.blended_threshold.value == assignment.shared_threshold.value


def test_fixed_shrinkage_lambda_one_reproduces_the_local_threshold_exactly() -> None:
    result = construct_fixed_shrinkage((CLIENT_A, CLIENT_B), FIXED_SHRINKAGE_PROTOCOL, QUANTILE)
    one_assignments = [a for a in result.assignments if a.lambda_weight.value == 1.0]
    assert one_assignments
    for assignment in one_assignments:
        assert assignment.blended_threshold.value == assignment.local_threshold.value


def test_fixed_shrinkage_covers_the_complete_declared_curve_for_every_client() -> None:
    result = construct_fixed_shrinkage((CLIENT_A, CLIENT_B), FIXED_SHRINKAGE_PROTOCOL, QUANTILE)
    weights_seen = {assignment.lambda_weight.value for assignment in result.assignments}
    assert weights_seen == {weight.value for weight in FIXED_SHRINKAGE_PROTOCOL.weights}
    assert len(result.assignments) == len(FIXED_SHRINKAGE_PROTOCOL.weights) * 2


def test_construct_size_aware_shrinkage_is_typed_unavailability() -> None:
    result = construct_size_aware_shrinkage(CLIENT_A.coordinate)
    assert result.reason is ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED
    assert result.detail
