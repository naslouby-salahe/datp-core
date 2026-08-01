"""Typed temporal quantities only; this module never executes temporal experiments."""

from dataclasses import dataclass

from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, Seed
from datp_core.protocols.metrics import TEMPORAL_CV_MATERIALITY_CUTOFF


@dataclass(frozen=True, slots=True)
class TemporalRecoveryResult:
    evidence_role: EvidenceRole
    seed: Seed
    static_reference_cv: MetricValue
    frozen_future_cv: MetricValue
    recalibrated_future_cv: MetricValue
    drift_excess: MetricValue
    recovered_amount: MetricValue
    recovery_ratio: MetricValue | None
    materiality_cutoff: MetricValue
    availability: AvailabilityStatus
    reason: str

    def __post_init__(self) -> None:
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal recovery requires temporal-boundary evidence")
        if self.availability is AvailabilityStatus.AVAILABLE and self.recovery_ratio is None:
            raise ValueError("available temporal recovery requires a ratio")
        if self.availability is not AvailabilityStatus.AVAILABLE and (
            self.recovery_ratio is not None or not self.reason
        ):
            raise ValueError("unavailable temporal recovery requires an explicit reason")


def temporal_recovery(
    *,
    seed: Seed,
    static_reference_cv: MetricValue,
    frozen_future_cv: MetricValue,
    recalibrated_future_cv: MetricValue,
) -> TemporalRecoveryResult:
    drift_excess = MetricValue(frozen_future_cv.value - static_reference_cv.value)
    recovered_amount = MetricValue(frozen_future_cv.value - recalibrated_future_cv.value)
    if drift_excess.value > TEMPORAL_CV_MATERIALITY_CUTOFF.value:
        return TemporalRecoveryResult(
            EvidenceRole.TEMPORAL_BOUNDARY,
            seed,
            static_reference_cv,
            frozen_future_cv,
            recalibrated_future_cv,
            drift_excess,
            recovered_amount,
            MetricValue(recovered_amount.value / drift_excess.value),
            TEMPORAL_CV_MATERIALITY_CUTOFF,
            AvailabilityStatus.AVAILABLE,
            "",
        )
    return TemporalRecoveryResult(
        EvidenceRole.TEMPORAL_BOUNDARY,
        seed,
        static_reference_cv,
        frozen_future_cv,
        recalibrated_future_cv,
        drift_excess,
        recovered_amount,
        None,
        TEMPORAL_CV_MATERIALITY_CUTOFF,
        AvailabilityStatus.UNDEFINED,
        "drift excess does not satisfy the declared positive-materiality rule",
    )
