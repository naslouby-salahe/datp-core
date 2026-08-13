from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from datp_core.core.identifiers import (
    AvailabilityStatus,
    ClaimWording,
    EvidenceRole,
    MetricId,
    NonEmptyString,
    NormalizedClaimWording,
    PopulationId,
    PopulationIdentityKind,
)
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


class ClaimReason(NonEmptyString):
    validation_name: ClassVar[str] = "claim reason"


class ClaimGuardPhrase(StrEnum):
    FORMAL_PRIVACY = "formal privacy"
    PRIVACY_GUARANTEE = "privacy guarantee"
    DEPLOYMENT_MEASUREMENT = "deployment measurement"
    MEASURED_DEPLOYMENT = "measured deployment"
    PHYSICAL_DEVICE = "physical device"
    FLEET_SCALE = "fleet-scale"
    DEMOGRAPHIC_FAIRNESS = "demographic fairness"
    PROTECTED_ATTRIBUTE = "protected attribute"
    CONTINUOUS_ADAPTATION = "continuous adaptation"
    ONLINE_ADAPTATION = "online adaptation"
    CONCEPT_DRIFT_SOLUTION = "concept drift solution"
    DRIFT_HANDLING = "drift handling"


_PRIVACY_GUARD_PHRASES = frozenset(
    {
        ClaimGuardPhrase.FORMAL_PRIVACY,
        ClaimGuardPhrase.PRIVACY_GUARANTEE,
    }
)
_DEPLOYMENT_GUARD_PHRASES = frozenset(
    {
        ClaimGuardPhrase.DEPLOYMENT_MEASUREMENT,
        ClaimGuardPhrase.MEASURED_DEPLOYMENT,
    }
)
_TEMPORAL_GUARD_PHRASES = frozenset(
    {
        ClaimGuardPhrase.CONTINUOUS_ADAPTATION,
        ClaimGuardPhrase.ONLINE_ADAPTATION,
        ClaimGuardPhrase.CONCEPT_DRIFT_SOLUTION,
        ClaimGuardPhrase.DRIFT_HANDLING,
    }
)
_EQUITY_GUARD_PHRASES = frozenset(
    {
        ClaimGuardPhrase.DEMOGRAPHIC_FAIRNESS,
        ClaimGuardPhrase.PROTECTED_ATTRIBUTE,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimRequest:
    kind: ClaimKind
    evidence_role: EvidenceRole
    metric: MetricId
    availability: AvailabilityStatus
    evidence_decision: EvidenceDecision
    verified_anchor_gate: VerifiedAnchorGateArtifact | None
    traffic_rate_available: bool
    wording: ClaimWording
    population: PopulationId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.wording, ClaimWording):
            object.__setattr__(self, "wording", ClaimWording(self.wording))
        if self.kind is ClaimKind.CONFIRMATORY and self.verified_anchor_gate is not None:
            if not self.verified_anchor_gate.permits_confirmatory_claims:
                raise ValueError("confirmatory claims cannot attach a non-permitting anchor-gate artifact")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimDecision:
    status: ClaimStatus
    wording: ClaimWording | None
    reason: ClaimReason

    def __post_init__(self) -> None:
        if self.wording is not None and not isinstance(self.wording, ClaimWording):
            object.__setattr__(self, "wording", ClaimWording(self.wording))
        if not isinstance(self.reason, ClaimReason):
            object.__setattr__(self, "reason", ClaimReason(self.reason))


def validate_claim(request: ClaimRequest) -> ClaimDecision:
    normalized_wording = NormalizedClaimWording(request.wording.casefold())
    failure = next((result for result in _claim_failures(request, normalized_wording) if result is not None), None)
    if failure is not None:
        return failure
    return (
        _confirmatory_result(request)
        if request.kind is ClaimKind.CONFIRMATORY
        else _final_nonconfirmatory_result(request)
    )


def _claim_failures(
    request: ClaimRequest, normalized_wording: NormalizedClaimWording
) -> Iterator[ClaimDecision | None]:

    yield _availability_failure(request)
    yield _suppressed_failure(request)
    yield _kind_role_mismatch(request)
    yield _confirmatory_anchor_gate_failure(request)
    yield _deployment_privacy_suppression(request)
    yield _operational_alert_burden_failure(request)
    yield _external_assignment_failure(request)
    yield _temporal_guard_result(request, normalized_wording)
    yield _privacy_guard_suppression(normalized_wording)
    yield _deployment_guard_suppression(normalized_wording)
    yield _equity_guard_suppression(normalized_wording)
    yield _applicability_boundary_failure(request, normalized_wording)


def _final_nonconfirmatory_result(request: ClaimRequest) -> ClaimDecision:
    supportive_result = _supportive_result(request)
    if supportive_result is not None:
        return supportive_result
    return ClaimDecision(
        status=ClaimStatus.PERMITTED,
        wording=request.wording,
        reason=ClaimReason("claim matches evidence scope"),
    )


def _availability_failure(request: ClaimRequest) -> ClaimDecision | None:
    if request.availability is not AvailabilityStatus.AVAILABLE:
        return _blocked(ClaimReason(f"claim evidence is {request.availability.value}"))
    return None


def _suppressed_failure(request: ClaimRequest) -> ClaimDecision | None:
    if request.evidence_decision is EvidenceDecision.SUPPRESSED:
        return _blocked(ClaimReason("suppressed experiments cannot be exported as executed evidence"))
    return None


def _confirmatory_anchor_gate_failure(request: ClaimRequest) -> ClaimDecision | None:
    if request.kind is ClaimKind.CONFIRMATORY:
        if request.verified_anchor_gate is None:
            return _blocked(ClaimReason("confirmatory claims require a verified anchor-gate artifact"))
        if not request.verified_anchor_gate.permits_confirmatory_claims:
            return _blocked(ClaimReason("the anchor gate blocks dependent journal claims"))
    return None


def _deployment_privacy_suppression(request: ClaimRequest) -> ClaimDecision | None:
    if request.kind in {ClaimKind.DEPLOYMENT, ClaimKind.PRIVACY}:
        return _suppressed(
            ClaimReason("DATP-Core provides neither deployment validation nor formal privacy guarantees")
        )
    return None


def _operational_alert_burden_failure(request: ClaimRequest) -> ClaimDecision | None:
    if (
        request.kind is ClaimKind.OPERATIONAL
        and request.metric is MetricId.ALERTS_PER_DAY
        and not request.traffic_rate_available
    ):
        return _blocked(ClaimReason("traffic-rate evidence is required for alert-burden translation"))
    return None


def _external_assignment_failure(request: ClaimRequest) -> ClaimDecision | None:
    if request.kind is ClaimKind.EXTERNAL and request.metric in {
        MetricId.TRUE_POSITIVE_RATE,
        MetricId.BALANCED_ACCURACY,
        MetricId.BINARY_MACRO_F1,
        MetricId.AUROC,
        MetricId.AVERAGE_PRECISION,
    }:
        return _blocked(ClaimReason("Edge external evidence has no valid client-level attack assignment"))
    return None


def _temporal_guard_result(request: ClaimRequest, normalized_wording: NormalizedClaimWording) -> ClaimDecision | None:
    if request.kind is ClaimKind.TEMPORAL:
        if any(phrase.value in normalized_wording for phrase in _TEMPORAL_GUARD_PHRASES):
            return _blocked(ClaimReason("one-shot recalibration cannot be represented as general drift handling"))
        if request.evidence_decision is not EvidenceDecision.SUPPORTED:
            return ClaimDecision(
                status=ClaimStatus.NARROWED,
                wording=ClaimWording(
                    f"[NARROWED:{request.evidence_decision.value}] Temporal boundary evidence is "
                    f"{request.evidence_decision.value} and does not support a positive recovery claim."
                ),
                reason=ClaimReason(f"temporal evidence is {request.evidence_decision.value}"),
            )
    return None


def _privacy_guard_suppression(normalized_wording: NormalizedClaimWording) -> ClaimDecision | None:
    if any(phrase.value in normalized_wording for phrase in _PRIVACY_GUARD_PHRASES):
        return _suppressed(ClaimReason("data locality is not a formal privacy guarantee"))
    return None


def _deployment_guard_suppression(normalized_wording: NormalizedClaimWording) -> ClaimDecision | None:
    if any(phrase.value in normalized_wording for phrase in _DEPLOYMENT_GUARD_PHRASES):
        return _suppressed(ClaimReason("message-size estimates are not deployment measurements"))
    return None


def _equity_guard_suppression(normalized_wording: NormalizedClaimWording) -> ClaimDecision | None:
    if any(phrase.value in normalized_wording for phrase in _EQUITY_GUARD_PHRASES):
        return _suppressed(ClaimReason("operational FPR equity is not demographic or protected-attribute fairness"))
    return None


def _applicability_boundary_failure(
    request: ClaimRequest, normalized_wording: NormalizedClaimWording
) -> ClaimDecision | None:
    if (
        request.population is not None
        and _is_nonphysical_population(request.population)
        and ClaimGuardPhrase.FLEET_SCALE.value in normalized_wording
    ):
        return _blocked(ClaimReason("synthetic or file-defined clients cannot support fleet-scale claims"))
    if request.evidence_role is EvidenceRole.APPLICABILITY_BOUNDARY and (
        _cites_file_defined_pseudo_clients(request.population)
        or ClaimGuardPhrase.PHYSICAL_DEVICE.value in normalized_wording
    ):
        return _blocked(ClaimReason("CIC file clients cannot be described as verified physical devices"))
    return None


def _confirmatory_result(request: ClaimRequest) -> ClaimDecision:
    if request.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
        return ClaimDecision(
            status=ClaimStatus.NARROWED,
            wording=ClaimWording(
                f"[NARROWED:control] Metric `{request.metric.value}` is a control or trade-off measure, "
                "not the confirmatory FPR equity endpoint."
            ),
            reason=ClaimReason("non-primary metrics are controls or trade-off evidence"),
        )
    if request.evidence_decision is not EvidenceDecision.SUPPORTED:
        return ClaimDecision(
            status=ClaimStatus.NARROWED,
            wording=ClaimWording(
                f"[NARROWED:{request.evidence_decision.value}] Confirmatory evidence is "
                f"{request.evidence_decision.value} and cannot support a positive claim."
            ),
            reason=ClaimReason(
                f"confirmatory evidence is {request.evidence_decision.value} and cannot support a positive claim"
            ),
        )
    return ClaimDecision(
        status=ClaimStatus.PERMITTED,
        wording=request.wording,
        reason=ClaimReason("claim matches evidence scope"),
    )


def _supportive_result(request: ClaimRequest) -> ClaimDecision | None:
    if request.kind is ClaimKind.SUPPORTIVE and request.evidence_decision is not EvidenceDecision.SUPPORTED:
        return ClaimDecision(
            status=ClaimStatus.NARROWED,
            wording=ClaimWording(
                f"[NARROWED:{request.evidence_decision.value}] Supportive evidence is "
                f"{request.evidence_decision.value} and cannot be exported as a positive claim."
            ),
            reason=ClaimReason(f"supportive evidence is {request.evidence_decision.value}"),
        )
    return None


_KIND_ROLE_BLOCKED_ROLES: dict[ClaimKind, frozenset[EvidenceRole]] = {
    ClaimKind.CONFIRMATORY: frozenset(role for role in EvidenceRole if role is not EvidenceRole.CONFIRMATORY),
    ClaimKind.EXTERNAL: frozenset(
        role
        for role in EvidenceRole
        if role not in {EvidenceRole.EXTERNAL_VALIDATION, EvidenceRole.APPLICABILITY_BOUNDARY}
    ),
    ClaimKind.TEMPORAL: frozenset(role for role in EvidenceRole if role is not EvidenceRole.TEMPORAL_BOUNDARY),
    ClaimKind.SUPPORTIVE: frozenset({EvidenceRole.CONFIRMATORY}),
    ClaimKind.OPERATIONAL: frozenset({EvidenceRole.CONFIRMATORY}),
}

_KIND_ROLE_MISMATCH_REASONS: dict[tuple[ClaimKind, EvidenceRole | None], ClaimReason] = {
    (ClaimKind.CONFIRMATORY, None): ClaimReason("only confirmatory evidence may support the sole confirmatory claim"),
    (ClaimKind.EXTERNAL, EvidenceRole.CONFIRMATORY): ClaimReason(
        "external evidence cannot be promoted to confirmatory evidence"
    ),
    (ClaimKind.EXTERNAL, None): ClaimReason(
        "external claims require external-validation or applicability-boundary evidence"
    ),
    (ClaimKind.TEMPORAL, EvidenceRole.CONFIRMATORY): ClaimReason(
        "temporal evidence cannot be promoted to confirmatory evidence"
    ),
    (ClaimKind.TEMPORAL, None): ClaimReason("temporal claims require temporal-boundary evidence"),
    (ClaimKind.SUPPORTIVE, None): ClaimReason("supportive claims cannot reuse confirmatory evidence role labeling"),
    (ClaimKind.OPERATIONAL, None): ClaimReason("operational claims cannot reuse confirmatory evidence role labeling"),
}


def _kind_role_mismatch(request: ClaimRequest) -> ClaimDecision | None:

    blocked_roles = _KIND_ROLE_BLOCKED_ROLES.get(request.kind, frozenset())
    if request.evidence_role not in blocked_roles:
        return None
    reason = _KIND_ROLE_MISMATCH_REASONS.get(
        (request.kind, request.evidence_role), _KIND_ROLE_MISMATCH_REASONS[(request.kind, None)]
    )
    return _blocked(reason)


def _blocked(reason: ClaimReason) -> ClaimDecision:
    return ClaimDecision(status=ClaimStatus.BLOCKED, wording=None, reason=reason)


def _suppressed(reason: ClaimReason) -> ClaimDecision:
    return ClaimDecision(status=ClaimStatus.SUPPRESSED, wording=None, reason=reason)


_POPULATION_IDENTITY_KINDS: dict[PopulationId, PopulationIdentityKind] = {
    declaration.id: declaration.identity_kind for declaration in POPULATIONS
}


def _cites_file_defined_pseudo_clients(population: PopulationId | None) -> bool:
    if population is None:
        return False
    return _POPULATION_IDENTITY_KINDS[population] is PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS


def _is_nonphysical_population(population: PopulationId) -> bool:
    return _POPULATION_IDENTITY_KINDS[population] in {
        PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS,
        PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
    }
