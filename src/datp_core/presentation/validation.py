"""Claim-control and final publication validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole, MetricId, PopulationId, PopulationIdentityKind
from datp_core.data.populations.declarations import POPULATIONS
from datp_core.experiments.anchor.contracts import VerifiedAnchorGateArtifact


class ClaimStatus(StrEnum):
    PERMITTED = "permitted"
    NARROWED = "narrowed"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    SUPPRESSED = "suppressed"


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
    NOT_ESTABLISHED = "not_established"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimRequest:
    kind: ClaimKind
    evidence_role: EvidenceRole
    metric: MetricId
    availability: AvailabilityStatus
    evidence_decision: EvidenceDecision
    verified_anchor_gate: VerifiedAnchorGateArtifact | None
    traffic_rate_available: bool
    wording: str #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    population: PopulationId | None = None

    def __post_init__(self) -> None:
        if not self.wording.strip():
            raise ValueError("claim requests require proposed wording")
        if self.kind is ClaimKind.CONFIRMATORY and self.verified_anchor_gate is not None:
            if not self.verified_anchor_gate.permits_confirmatory_claims:
                raise ValueError("confirmatory claims cannot attach a non-permitting anchor-gate artifact")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimDecision:
    status: ClaimStatus
    wording: str#TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    reason: str#TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    anchor_gate_checksum: Checksum | None = None


def validate_claim(request: ClaimRequest) -> ClaimDecision:
    normalized_wording = request.wording.casefold()
    if request.availability is not AvailabilityStatus.AVAILABLE:
        return _blocked(f"claim evidence is {request.availability.value}")
    if request.evidence_decision is EvidenceDecision.SUPPRESSED:
        return _blocked("suppressed experiments cannot be exported as executed evidence")
    kind_role_failure = _kind_role_mismatch(request)
    if kind_role_failure is not None:
        return kind_role_failure
    if request.kind is ClaimKind.CONFIRMATORY:
        if request.verified_anchor_gate is None:
            return _blocked("confirmatory claims require a checksum-verified anchor-gate artifact")
        if not request.verified_anchor_gate.permits_confirmatory_claims:
            return _blocked("the anchor gate blocks dependent journal claims")
    if request.kind in {ClaimKind.DEPLOYMENT, ClaimKind.PRIVACY}:
        return _suppressed("DATP-Core provides neither deployment validation nor formal privacy guarantees")
    if request.kind is ClaimKind.OPERATIONAL and request.metric is MetricId.ALERTS_PER_DAY:
        if not request.traffic_rate_available:
            return _blocked("traffic-rate evidence is required for alert-burden translation")
    if request.kind is ClaimKind.EXTERNAL:
        if request.metric in {
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BALANCED_ACCURACY,
            MetricId.BINARY_MACRO_F1,
            MetricId.AUROC,
        }:
            return _blocked("Edge external evidence has no valid client-level attack assignment")
    if request.kind is ClaimKind.TEMPORAL:
        if any(
            phrase in normalized_wording
            for phrase in ("continuous adaptation", "online adaptation", "concept drift solution", "drift handling")
        ):
            return _blocked("one-shot recalibration cannot be represented as general drift handling")
        if request.evidence_decision is not EvidenceDecision.SUPPORTED:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=(
                    f"[NARROWED:{request.evidence_decision.value}] Temporal boundary evidence is "
                    f"{request.evidence_decision.value} and does not support a positive recovery claim."
                ),
                reason=f"temporal evidence is {request.evidence_decision.value}",
            )
    if "formal privacy" in normalized_wording or "privacy guarantee" in normalized_wording: #TODO: use enum and also make sure to check and adapt the whole package
        return _suppressed("data locality is not a formal privacy guarantee")
    if "deployment measurement" in normalized_wording or "measured deployment" in normalized_wording:
        return _suppressed("message-size estimates are not deployment measurements")
    if request.evidence_role is EvidenceRole.APPLICABILITY_BOUNDARY and (
        _cites_file_defined_pseudo_clients(request.population) or "physical device" in normalized_wording
    ):
        return _blocked("CIC file clients cannot be described as verified physical devices")
    if request.kind is ClaimKind.CONFIRMATORY:
        if request.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=(
                    f"[NARROWED:control] Metric `{request.metric.value}` is a control or trade-off measure, "
                    "not the confirmatory FPR equity endpoint."
                ),
                reason="non-primary metrics are controls or trade-off evidence",
                anchor_gate_checksum=(
                    None if request.verified_anchor_gate is None else request.verified_anchor_gate.artifact_checksum
                ),
            )
        if request.evidence_decision is not EvidenceDecision.SUPPORTED:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=(
                    f"[NARROWED:{request.evidence_decision.value}] Confirmatory evidence is "
                    f"{request.evidence_decision.value} and cannot support a positive claim."
                ),
                reason=(
                    f"confirmatory evidence is {request.evidence_decision.value} and cannot support a positive claim"
                ),
                anchor_gate_checksum=(
                    None if request.verified_anchor_gate is None else request.verified_anchor_gate.artifact_checksum
                ),
            )
        return ClaimDecision(
            status=ClaimStatus.PERMITTED,
            wording=request.wording,
            reason="claim matches evidence scope",
            anchor_gate_checksum=request.verified_anchor_gate.artifact_checksum
            if request.verified_anchor_gate is not None
            else None,
        )
    if request.kind is ClaimKind.SUPPORTIVE and request.evidence_decision is not EvidenceDecision.SUPPORTED:
        return ClaimDecision(
            status=ClaimStatus.NARROWED,
            wording=(
                f"[NARROWED:{request.evidence_decision.value}] Supportive evidence is "
                f"{request.evidence_decision.value} and cannot be exported as a positive claim."
            ),
            reason=f"supportive evidence is {request.evidence_decision.value}",
        )
    return ClaimDecision(status=ClaimStatus.PERMITTED, wording=request.wording, reason="claim matches evidence scope")


def _kind_role_mismatch(request: ClaimRequest) -> ClaimDecision | None:
    """Reject claim kinds that do not match the evidence role they cite."""
    match request.kind:
        case ClaimKind.CONFIRMATORY:
            if request.evidence_role is not EvidenceRole.CONFIRMATORY:
                return _blocked("only confirmatory evidence may support the sole confirmatory claim")
        case ClaimKind.EXTERNAL:
            if request.evidence_role is EvidenceRole.CONFIRMATORY:
                return _blocked("external evidence cannot be promoted to confirmatory evidence")
            if request.evidence_role not in {
                EvidenceRole.EXTERNAL_VALIDATION,
                EvidenceRole.APPLICABILITY_BOUNDARY,
            }:
                return _blocked("external claims require external-validation or applicability-boundary evidence")
        case ClaimKind.TEMPORAL:
            if request.evidence_role is EvidenceRole.CONFIRMATORY:
                return _blocked("temporal evidence cannot be promoted to confirmatory evidence")
            if request.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
                return _blocked("temporal claims require temporal-boundary evidence")
        case ClaimKind.SUPPORTIVE:
            if request.evidence_role is EvidenceRole.CONFIRMATORY:
                return _blocked("supportive claims cannot reuse confirmatory evidence role labeling")
        case ClaimKind.OPERATIONAL:
            if request.evidence_role is EvidenceRole.CONFIRMATORY:
                return _blocked("operational claims cannot reuse confirmatory evidence role labeling")
        case ClaimKind.DEPLOYMENT | ClaimKind.PRIVACY:
            return None
    return None


def _blocked(reason: str) -> ClaimDecision: #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    return ClaimDecision(status=ClaimStatus.BLOCKED, wording="", reason=reason)


def _suppressed(reason: str) -> ClaimDecision: #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    return ClaimDecision(status=ClaimStatus.SUPPRESSED, wording="", reason=reason)


_POPULATION_IDENTITY_KINDS: dict[PopulationId, PopulationIdentityKind] = {
    declaration.id: declaration.identity_kind for declaration in POPULATIONS
}


def _cites_file_defined_pseudo_clients(population: PopulationId | None) -> bool:
    if population is None:
        return False
    return _POPULATION_IDENTITY_KINDS[population] is PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS
