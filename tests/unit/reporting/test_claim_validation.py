from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, MetricId
from datp_core.reporting.validation import ClaimKind, ClaimRequest, validate_claim


def test_unavailable_claim_is_blocked() -> None:
    decision = validate_claim(
        ClaimRequest(
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
        ClaimRequest(
            kind=ClaimKind.PRIVACY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=AvailabilityStatus.AVAILABLE,
            wording="DATP-Core is privacy preserving",
        )
    )
    assert not decision.wording
