"""Per-client threshold and operating-point movement evidence."""

from typing import ClassVar

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values.ratios import MetricValue, Ratio, ThresholdValue


class ThresholdOperatingPoint(StrictModel):
    threshold: ThresholdValue
    fpr: Ratio
    tpr: Ratio | None


class ThresholdMovement(StrictModel):
    client: ClientIdentity
    delta_threshold: MetricValue
    delta_fpr: MetricValue
    delta_tpr: MetricValue | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @property
    def attack_availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.delta_tpr is not None else AvailabilityStatus.UNAVAILABLE

    @property
    def reason(self) -> str | None:
        return None if self.delta_tpr is not None else "attack-sensitive movement unavailable"


def threshold_movement(
    *,
    client: ClientIdentity,
    shared: ThresholdOperatingPoint,
    local: ThresholdOperatingPoint,
) -> ThresholdMovement:
    if (shared.tpr is None) != (local.tpr is None):
        raise ValueError("TPR movement requires both operating points or neither")
    if shared.tpr is None:
        delta_tpr = None
    else:
        local_tpr = local.tpr
        if local_tpr is None:
            raise ValueError("TPR movement requires both operating points or neither")
        delta_tpr = MetricValue(local_tpr.value - shared.tpr.value)
    return ThresholdMovement(
        client=client,
        delta_threshold=MetricValue(local.threshold.value - shared.threshold.value),
        delta_fpr=MetricValue(local.fpr.value - shared.fpr.value),
        delta_tpr=delta_tpr,
    )
