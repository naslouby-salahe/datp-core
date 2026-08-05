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


class EvidenceDecision(StrEnum):
    SUPPORTED = "supported"
    DIRECTIONAL_INCONCLUSIVE = "directional_inconclusive"
    NULL = "null"
    REVERSED = "reversed"
    UNSTABLE = "unstable"
    BOUNDARY = "boundary"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimRequest:
    kind: ClaimKind
    evidence_role: EvidenceRole
    metric: MetricId
    availability: AvailabilityStatus
    evidence_decision: EvidenceDecision
    anchor_gate_passed: bool
    traffic_rate_available: bool
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
    normalized_wording = request.wording.casefold()
    if request.availability is not AvailabilityStatus.AVAILABLE:
        return _blocked(f"claim evidence is {request.availability.value}")
    if request.evidence_decision is EvidenceDecision.SUPPRESSED:
        return _blocked("suppressed experiments cannot be exported as executed evidence")
    if request.kind is ClaimKind.CONFIRMATORY and not request.anchor_gate_passed:
        return _blocked("the anchor gate blocks dependent journal claims")
    if request.kind in {ClaimKind.DEPLOYMENT, ClaimKind.PRIVACY}:
        return _suppressed("DATP-Core provides neither deployment validation nor formal privacy guarantees")
    if request.kind is ClaimKind.OPERATIONAL and request.metric is MetricId.ALERTS_PER_DAY:
        if not request.traffic_rate_available:
            return _blocked("traffic-rate evidence is required for alert-burden translation")
    if request.kind is ClaimKind.EXTERNAL:
        if request.evidence_role is EvidenceRole.CONFIRMATORY:
            return _blocked("external evidence cannot be promoted to confirmatory evidence")
        if request.metric in {
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BALANCED_ACCURACY,
            MetricId.BINARY_MACRO_F1,
            MetricId.AUROC,
        }:
            return _blocked("Edge external evidence has no valid client-level attack assignment")
    if request.kind is ClaimKind.TEMPORAL and any(
        phrase in normalized_wording
        for phrase in ("continuous adaptation", "online adaptation", "concept drift solution", "drift handling")
    ):
        return _blocked("one-shot recalibration cannot be represented as general drift handling")
    if "formal privacy" in normalized_wording or "privacy guarantee" in normalized_wording:
        return _suppressed("data locality is not a formal privacy guarantee")
    if "deployment measurement" in normalized_wording or "measured deployment" in normalized_wording:
        return _suppressed("message-size estimates are not deployment measurements")
    if "physical device" in normalized_wording and request.evidence_role is EvidenceRole.APPLICABILITY_BOUNDARY:
        return _blocked("CIC file clients cannot be described as verified physical devices")
    if request.kind is ClaimKind.CONFIRMATORY:
        if request.evidence_role is not EvidenceRole.CONFIRMATORY:
            return _blocked("only confirmatory evidence may support the sole confirmatory claim")
        if request.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=request.wording,
                reason="non-primary metrics are controls or trade-off evidence",
            )
        if request.evidence_decision is not EvidenceDecision.SUPPORTED:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=request.wording,
                reason=(
                    f"confirmatory evidence is {request.evidence_decision.value} and cannot support a positive claim"
                ),
            )
    return ClaimDecision(status=ClaimStatus.PERMITTED, wording=request.wording, reason="claim matches evidence scope")


def _blocked(reason: str) -> ClaimDecision:
    return ClaimDecision(status=ClaimStatus.BLOCKED, wording="", reason=reason)


def _suppressed(reason: str) -> ClaimDecision:
    return ClaimDecision(status=ClaimStatus.SUPPRESSED, wording="", reason=reason)
