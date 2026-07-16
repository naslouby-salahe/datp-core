from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.operating_points import ClientEligibilityReason, ClientEligibilityStatus
from datp_core.domain.evaluation.statistical_results import CoverageRatio, Probability
from datp_core.domain.thresholding.clustering import CANONICAL_CLUSTER_K

CANONICAL_CLUSTER_COUNT: Final = CANONICAL_CLUSTER_K.value
PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES: Final = CalibrationSampleCount(value=100)
REGIME_D_MINIMUM_COVERAGE: Final = CoverageRatio(value=Decimal("0.90"))
REGIME_D_TEMPORAL_HISTORICAL_FRACTION: Final = Probability(value=Decimal("0.70"))
REGIME_A_STATIC_SPLIT_TRAIN_FRACTION: Final = Probability(value=Decimal("0.60"))
REGIME_A_STATIC_SPLIT_GAP_FRACTION: Final = Probability(value=Decimal("0.01"))
REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION: Final = Probability(value=Decimal("0.20"))


def _validated_integer(value: object, *, name: str, minimum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainValidationError(detail=f"{name} must be an integer", value=repr(value), constraint="integer")
    if value < minimum:
        raise DomainValidationError(
            detail=f"{name} must be an integer greater than or equal to {minimum}",
            value=repr(value),
            constraint=f"integer >= {minimum}",
        )
    return value


def is_canonical_k(*, cluster_count: int) -> bool:
    return not isinstance(cluster_count, bool) and cluster_count == CANONICAL_CLUSTER_COUNT


def has_minimum_eligible_calibration_count(*, calibration_count: int, minimum_count: int) -> bool:
    validated_calibration_count = _validated_integer(calibration_count, name="calibration count", minimum=0)
    validated_minimum_count = _validated_integer(minimum_count, name="minimum count", minimum=1)
    return validated_calibration_count >= validated_minimum_count


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ProtocolEligibilitySpec:
    minimum_calibration_samples: CalibrationSampleCount

    def __init__(self) -> None:
        object.__setattr__(self, "minimum_calibration_samples", PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES)


@dataclass(frozen=True, slots=True, kw_only=True)
class EligibilityClassification:
    status: ClientEligibilityStatus
    reason: ClientEligibilityReason


def classify_protocol_eligibility(
    *, calibration_count: CalibrationSampleCount, specification: ProtocolEligibilitySpec
) -> EligibilityClassification:
    if calibration_count.value >= specification.minimum_calibration_samples.value:
        return EligibilityClassification(
            status=ClientEligibilityStatus.ELIGIBLE,
            reason=ClientEligibilityReason.SUFFICIENT_CALIBRATION,
        )
    return EligibilityClassification(
        status=ClientEligibilityStatus.FALLBACK_ASSIGNED,
        reason=ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK,
    )
