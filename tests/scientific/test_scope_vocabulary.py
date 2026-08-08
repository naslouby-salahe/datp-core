from datp_core.analysis.metrics.models import WarningCode
from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole, MetricId, TemporalState
from datp_core.presentation.validation import ClaimStatus


def test_report_facing_enums_preserve_claim_boundaries() -> None:
    claim_values = {status.value for status in ClaimStatus}
    assert claim_values == {"permitted", "narrowed", "blocked", "unsupported", "suppressed"}
    assert "attack_detection_equity" not in claim_values
    assert "privacy_preserving" not in claim_values
    assert "deployment_validated" not in claim_values
    assert "concept_drift_handling" not in claim_values


def test_detector_quality_control_is_not_a_threshold_policy_outcome() -> None:
    assert MetricId.AUROC.value == "auroc"
    assert MetricId.AUROC not in {MetricId.FPR_COEFFICIENT_OF_VARIATION, MetricId.MEAN_FPR}


def test_external_attack_unavailability_and_bounded_recalibration_are_expressible() -> None:
    assert AvailabilityStatus.UNAVAILABLE.value == "unavailable"
    assert WarningCode.UNAVAILABLE_ATTACK_ASSIGNMENT.value == "unavailable_attack_assignment"
    assert tuple(TemporalState) == (
        TemporalState.STATIC_REFERENCE,
        TemporalState.FROZEN_FUTURE,
        TemporalState.RECALIBRATED_FUTURE,
    )
    assert all("continuous" not in state.value and "drift" not in state.value for state in TemporalState)


def test_evidence_roles_cannot_promote_supporting_work_to_confirmation() -> None:
    assert EvidenceRole.CONFIRMATORY.value == "confirmatory"
    assert EvidenceRole.EXTERNAL_VALIDATION.value != EvidenceRole.CONFIRMATORY.value
    assert EvidenceRole.OPERATIONAL_TRANSLATION.value != EvidenceRole.CONFIRMATORY.value
