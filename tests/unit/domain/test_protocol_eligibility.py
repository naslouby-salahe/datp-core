from dataclasses import MISSING, fields
from decimal import Decimal

import pytest

from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.operating_points import ClientEligibilityReason, ClientEligibilityStatus
from datp_core.domain.mathematics.pooled_statistics import (
    PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES,
    REGIME_D_TEMPORAL_HISTORICAL_FRACTION,
    ProtocolEligibilitySpec,
    classify_protocol_eligibility,
)


def test_locked_protocol_constants_have_the_authoritative_values_and_no_hidden_default() -> None:
    assert PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES.value == 100
    assert REGIME_D_TEMPORAL_HISTORICAL_FRACTION.value == Decimal("0.700000000000")
    assert fields(ProtocolEligibilitySpec)[0].default is MISSING

    specification = ProtocolEligibilitySpec(minimum_calibration_samples=PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES)

    assert specification.minimum_calibration_samples is PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES

    with pytest.raises(TypeError):
        type.__call__(ProtocolEligibilitySpec)


@pytest.mark.parametrize(
    ("count", "status", "reason"),
    [
        (
            99,
            ClientEligibilityStatus.FALLBACK_ASSIGNED,
            ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK,
        ),
        (100, ClientEligibilityStatus.ELIGIBLE, ClientEligibilityReason.SUFFICIENT_CALIBRATION),
        (101, ClientEligibilityStatus.ELIGIBLE, ClientEligibilityReason.SUFFICIENT_CALIBRATION),
    ],
)
def test_protocol_eligibility_classifies_the_locked_threshold_boundary(
    count: int, status: ClientEligibilityStatus, reason: ClientEligibilityReason
) -> None:
    result = classify_protocol_eligibility(
        calibration_count=CalibrationSampleCount(value=count),
        specification=ProtocolEligibilitySpec(
            minimum_calibration_samples=PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES
        ),
    )

    assert result.status is status
    assert result.reason is reason
