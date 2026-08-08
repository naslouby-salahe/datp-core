from hypothesis import given
from hypothesis import strategies as st
from tests.unit.thresholding.helpers import identity

from datp_core.core.numeric import ShrinkageWeight, ThresholdValue
from datp_core.thresholds.variants.shrinkage import ShrinkageAssignment

CLIENT = identity("client_a")
_VALUE = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)


@given(local=_VALUE, shared=_VALUE)
def test_shrinkage_lambda_zero_reproduces_the_shared_threshold_exactly(
    local: float,
    shared: float,
) -> None:
    assignment = ShrinkageAssignment(
        client=CLIENT,
        lambda_weight=ShrinkageWeight(0.0),
        local_threshold=ThresholdValue(local),
        shared_threshold=ThresholdValue(shared),
        blended_threshold=ThresholdValue(shared),
    )
    assert assignment.blended_threshold.value == shared


@given(local=_VALUE, shared=_VALUE)
def test_shrinkage_lambda_one_reproduces_the_local_threshold_exactly(
    local: float,
    shared: float,
) -> None:
    assignment = ShrinkageAssignment(
        client=CLIENT,
        lambda_weight=ShrinkageWeight(1.0),
        local_threshold=ThresholdValue(local),
        shared_threshold=ThresholdValue(shared),
        blended_threshold=ThresholdValue(local),
    )
    assert assignment.blended_threshold.value == local


@given(
    local=_VALUE,
    shared=_VALUE,
    weight=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_shrinkage_blend_always_lies_between_local_and_shared(
    local: float,
    shared: float,
    weight: float,
) -> None:
    blended_value = weight * local + (1 - weight) * shared
    assignment = ShrinkageAssignment(
        client=CLIENT,
        lambda_weight=ShrinkageWeight(weight),
        local_threshold=ThresholdValue(local),
        shared_threshold=ThresholdValue(shared),
        blended_threshold=ThresholdValue(blended_value),
    )
    lower_bound, upper_bound = sorted((local, shared))
    assert lower_bound - 1e-9 <= assignment.blended_threshold.value <= upper_bound + 1e-9
