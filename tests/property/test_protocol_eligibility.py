from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.operating_points import ClientEligibilityStatus
from datp_core.domain.mathematics.pooled_statistics import (
    PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES,
    ProtocolEligibilitySpec,
    classify_protocol_eligibility,
)


@given(st.integers(min_value=0, max_value=10_000))
def test_protocol_eligibility_is_monotonic_across_the_exact_locked_threshold(count: int) -> None:
    specification = ProtocolEligibilitySpec(minimum_calibration_samples=PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES)
    current = classify_protocol_eligibility(
        calibration_count=CalibrationSampleCount(value=count), specification=specification
    )
    higher = classify_protocol_eligibility(
        calibration_count=CalibrationSampleCount(value=max(count, 100)), specification=specification
    )

    assert higher.status is ClientEligibilityStatus.ELIGIBLE
    if current.status is ClientEligibilityStatus.ELIGIBLE:
        assert higher.status is ClientEligibilityStatus.ELIGIBLE
