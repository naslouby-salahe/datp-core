from dataclasses import MISSING, fields
from decimal import Decimal

import pytest

from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.operating_points import ClientEligibilityReason, ClientEligibilityStatus
from datp_core.domain.mathematics.pooled_statistics import (
    PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES,
    REGIME_D_MINIMUM_COVERAGE,
    REGIME_D_TEMPORAL_HISTORICAL_FRACTION,
    ProtocolEligibilitySpec,
    classify_protocol_eligibility,
)


def test_locked_protocol_constants_have_the_authoritative_values_and_single_specification_path() -> None:
    specification = ProtocolEligibilitySpec()

    assert PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES.value == 100
    assert REGIME_D_MINIMUM_COVERAGE.value == Decimal("0.900000000000")
    assert REGIME_D_TEMPORAL_HISTORICAL_FRACTION.value == Decimal("0.700000000000")
    assert specification.minimum_calibration_samples is PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES
    assert fields(ProtocolEligibilitySpec)[0].default is MISSING
    with pytest.raises(TypeError):
        type.__call__(ProtocolEligibilitySpec, minimum_calibration_samples=CalibrationSampleCount(value=99))


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
        specification=ProtocolEligibilitySpec(),
    )

    assert result.status is status
    assert result.reason is reason
