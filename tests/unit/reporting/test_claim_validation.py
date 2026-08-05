from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, MetricId
from datp_core.reporting.validation import (
    ClaimKind,
    ClaimRequest,
    EvidenceDecision,
    validate_claim,
)


def claim_request(
    *,
    kind: ClaimKind,
    evidence_role: EvidenceRole,
    metric: MetricId,
    wording: str,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    evidence_decision: EvidenceDecision = EvidenceDecision.SUPPORTED,
    anchor_gate_passed: bool = True,
    traffic_rate_available: bool = False,
) -> ClaimRequest:
    return ClaimRequest(
        kind=kind,
        evidence_role=evidence_role,
        metric=metric,
        availability=availability,
        evidence_decision=evidence_decision,
        anchor_gate_passed=anchor_gate_passed,
        traffic_rate_available=traffic_rate_available,
        wording=wording,
    )


def test_unavailable_claim_is_blocked() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
            metric=MetricId.TRUE_POSITIVE_RATE,
            availability=AvailabilityStatus.UNAVAILABLE,
            wording="attack performance generalizes to Edge clients",
        )
    )
    assert not decision.wording


def test_formal_privacy_claim_is_suppressed() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.PRIVACY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="DATP-Core provides a formal privacy guarantee",
        )
    )
    assert not decision.wording


def test_blocked_anchor_blocks_confirmatory_claim() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            anchor_gate_passed=False,
            wording="Local calibration improves cross-client FPR equity",
        )
    )
    assert not decision.wording


def test_inconclusive_confirmatory_result_cannot_render_as_positive_support() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            evidence_decision=EvidenceDecision.DIRECTIONAL_INCONCLUSIVE,
            wording="Local calibration improves cross-client FPR equity",
        )
    )
    assert decision.wording
    assert "cannot support a positive claim" in decision.reason


def test_edge_attack_sensitive_claim_is_blocked() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
            metric=MetricId.TRUE_POSITIVE_RATE,
            wording="Edge client-level attack detection improves",
        )
    )
    assert not decision.wording


def test_one_shot_recalibration_cannot_be_called_continuous_adaptation() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.TEMPORAL,
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            metric=MetricId.FALSE_POSITIVE_RATE,
            wording="The method provides continuous adaptation under concept drift",
        )
    )
    assert not decision.wording


def test_alert_burden_requires_traffic_rate_evidence() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.OPERATIONAL,
            evidence_role=EvidenceRole.OPERATIONAL_TRANSLATION,
            metric=MetricId.ALERTS_PER_DAY,
            wording="The policy produces fewer alerts per day",
        )
    )
    assert not decision.wording
