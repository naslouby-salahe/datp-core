import pytest

from datp_core.core.identifiers import AvailabilityStatus, ClaimWording, EvidenceRole, MetricId, PopulationId
from datp_core.experiments.anchor.contracts import VerifiedAnchorGateArtifact
from datp_core.presentation.export import _descriptive_evidence_claim
from datp_core.presentation.validation import (
    ClaimKind,
    ClaimRequest,
    ClaimStatus,
    EvidenceDecision,
    validate_claim,
)


def test_claim_status_member_set_is_exact_and_unique() -> None:
    assert set(ClaimStatus.__members__) == {"PERMITTED", "NARROWED", "BLOCKED", "UNSUPPORTED", "SUPPRESSED"}
    values = tuple(member.value for member in ClaimStatus)
    assert len(values) == len(set(values))
    assert all(value.islower() for value in values)


def test_supportive_descriptive_publication_claim_retains_its_evidence_tier() -> None:
    claim = _descriptive_evidence_claim(EvidenceRole.SUPPORTIVE)

    assert claim.status is ClaimStatus.NARROWED
    assert claim.wording is not None
    assert "Supportive evidence" in claim.wording
    assert claim.reason == "supportive evidence tier"


def claim_request(
    *,
    kind: ClaimKind,
    evidence_role: EvidenceRole,
    metric: MetricId,
    wording: str | ClaimWording,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    evidence_decision: EvidenceDecision = EvidenceDecision.SUPPORTED,
    verified_anchor_gate: VerifiedAnchorGateArtifact | None = None,
    traffic_rate_available: bool = False,
    population: PopulationId | None = None,
) -> ClaimRequest:
    return ClaimRequest(
        kind=kind,
        evidence_role=evidence_role,
        metric=metric,
        availability=availability,
        evidence_decision=evidence_decision,
        verified_anchor_gate=verified_anchor_gate,
        traffic_rate_available=traffic_rate_available,
        wording=wording if isinstance(wording, ClaimWording) else ClaimWording(wording),
        population=population,
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


def test_operational_equity_cannot_be_called_demographic_fairness() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="The policy establishes demographic fairness across protected attributes",
        )
    )

    assert decision.status is ClaimStatus.SUPPRESSED
    assert "operational FPR equity" in decision.reason


@pytest.mark.parametrize(
    ("wording", "reason"),
    [
        ("This is the first federated anomaly-threshold method", "absolute novelty"),
        ("The only valid calibration approach", "absolute novelty"),
        ("State-of-the-art operating-point equity", "absolute novelty"),
        ("Byzantine-robust calibration", "protocol-compliant"),
        ("Secure aggregation makes this calibrated threshold trustworthy", "protocol-compliant"),
        ("Intermittent cross-device clients receive the same personalization benefit", "persistent identifiable"),
        ("An unseen client receives a personalized threshold", "persistent identifiable"),
    ],
)
def test_claims_cannot_overstate_novelty_or_adversarial_calibration_scope(wording: str, reason: str) -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording=wording,
        )
    )

    assert decision.status is ClaimStatus.SUPPRESSED
    assert reason in decision.reason


@pytest.mark.parametrize("wording", (
    "This is a new federated-learning optimizer",
    "This is a complete FL-IDS framework benchmark",
    "This is a privacy-preserving security system",
    "This is a robust federated-learning defense",
    "This is a drift-adaptive production IDS",
    "This is a fleet-scale deployment",
    "This is a universal thresholding method",
    "The method improves every client",
    "The method improves global Macro-F1",
    "This is a solution to non-IID federated learning",
))
def test_claims_cannot_use_prohibited_central_framing(wording: str) -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording=wording,
        )
    )

    assert decision.status is ClaimStatus.SUPPRESSED
    assert "locked threshold-scope" in decision.reason


def test_blocked_anchor_blocks_confirmatory_claim() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            verified_anchor_gate=None,
            wording="Local calibration improves cross-client FPR equity",
        )
    )
    assert not decision.wording
    assert "anchor-gate artifact" in decision.reason


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
    if decision.wording is not None:
        assert decision.status is ClaimStatus.BLOCKED or "[NARROWED:" in decision.wording
    if decision.status is ClaimStatus.NARROWED:
        assert decision.wording is not None
        assert decision.wording.startswith("[NARROWED:")
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


def test_edge_average_precision_claim_is_blocked_without_attack_assignment() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
            metric=MetricId.AVERAGE_PRECISION,
            wording="Edge client-level average precision improves",
        )
    )
    assert not decision.wording


@pytest.mark.parametrize("wording", (
    "The method provides continuous adaptation under concept drift",
    "The method performs online learning after deployment",
    "The method supplies streaming drift detection",
    "The method uses drift-triggered recalibration",
    "The method establishes production stability over repeated cycles",
))
def test_one_shot_recalibration_cannot_be_called_general_drift_handling(wording: str) -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.TEMPORAL,
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            metric=MetricId.FALSE_POSITIVE_RATE,
            wording=wording,
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


def test_supportive_claim_cannot_reuse_confirmatory_evidence_role() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="Supportive evidence strengthens the confirmatory claim",
        )
    )
    assert decision.status is ClaimStatus.BLOCKED
    assert "confirmatory evidence role" in decision.reason


def test_supportive_null_evidence_cannot_render_as_positive_support() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            evidence_decision=EvidenceDecision.NULL,
            wording="Supportive threshold construction improved equity",
        )
    )
    assert decision.status is ClaimStatus.NARROWED
    assert decision.wording is not None
    assert decision.wording.startswith("[NARROWED:")


def test_physical_device_claim_blocked_by_literal_wording() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="CIC file clients behave as verified physical device deployments",
        )
    )
    assert decision.status is ClaimStatus.BLOCKED
    assert "physical devices" in decision.reason


def test_physical_device_claim_blocked_by_population_identity_kind_even_when_reworded() -> None:

    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="device-level hardware evidence",
            population=PopulationId.CICIOT_FILE_CLIENTS,
        )
    )
    assert decision.status is ClaimStatus.BLOCKED
    assert "physical devices" in decision.reason


def test_applicability_boundary_claim_permitted_for_non_pseudo_client_population() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="N-BaIoT applicability boundary evidence remains claim-bounded",
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
        )
    )
    assert decision.status is ClaimStatus.PERMITTED


def test_fleet_scale_claim_is_blocked_for_file_defined_clients() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="CIC evidence establishes fleet-scale operating-point behavior",
            population=PopulationId.CICIOT_FILE_CLIENTS,
        )
    )

    assert decision.status is ClaimStatus.BLOCKED
    assert "fleet-scale" in decision.reason


def test_fleet_scale_claim_is_blocked_for_synthetic_clients() -> None:
    decision = validate_claim(
        claim_request(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            wording="Synthetic partitions establish fleet-scale behavior",
            population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        )
    )

    assert decision.status is ClaimStatus.BLOCKED
    assert "fleet-scale" in decision.reason
