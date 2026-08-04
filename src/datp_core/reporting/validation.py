"""Claim-control and final publication validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import AvailabilityStatus, ClaimStatus, EvidenceRole, MetricId


class ClaimKind(StrEnum):
    CONFIRMATORY = "confirmatory"
    SUPPORTIVE = "supportive"
    EXTERNAL = "external"
    TEMPORAL = "temporal"
    OPERATIONAL = "operational"
    DEPLOYMENT = "deployment"
    PRIVACY = "privacy"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimRequest:
    kind: ClaimKind
    evidence_role: EvidenceRole
    metric: MetricId
    availability: AvailabilityStatus
    wording: str

    def __post_init__(self) -> None:
        if not self.wording.strip():
            raise ValueError("claim requests require proposed wording")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimDecision:
    status: ClaimStatus
    wording: str
    reason: str


def validate_claim(request: ClaimRequest) -> ClaimDecision:
    if request.availability is not AvailabilityStatus.AVAILABLE:
        return ClaimDecision(
            status=ClaimStatus.BLOCKED,
            wording="",
            reason=f"claim evidence is {request.availability.value}",
        )
    if request.kind in {ClaimKind.DEPLOYMENT, ClaimKind.PRIVACY}:
        return ClaimDecision(
            status=ClaimStatus.SUPPRESSED,
            wording="",
            reason="DATP-Core provides neither deployment validation nor formal privacy guarantees",
        )
    if request.kind is ClaimKind.OPERATIONAL and request.metric is MetricId.ALERTS_PER_DAY:
        return ClaimDecision(
            status=ClaimStatus.BLOCKED,
            wording="",
            reason="traffic-rate evidence is required for alert-burden translation",
        )
    if request.kind is ClaimKind.CONFIRMATORY:
        if request.evidence_role is not EvidenceRole.CONFIRMATORY:
            return ClaimDecision(
                status=ClaimStatus.BLOCKED,
                wording="",
                reason="only confirmatory evidence may support the sole confirmatory claim",
            )
        if request.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=request.wording,
                reason="non-primary metrics are controls or trade-off evidence",
            )
    return ClaimDecision(status=ClaimStatus.PERMITTED, wording=request.wording, reason="claim matches evidence scope")
