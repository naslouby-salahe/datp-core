from pathlib import Path

from datp_core.domain.enums import AvailabilityStatus, ClaimStatus, EvidenceRole, MetricId
from datp_core.reporting.export import PublicationBundle, export_markdown
from datp_core.reporting.tables import PublicationTable, TableCell
from datp_core.reporting.validation import (
    ClaimKind,
    ClaimRequest,
    EvidenceDecision,
    validate_claim,
)


def test_reporting_export_is_deterministic_and_preserves_unavailable_outcomes(tmp_path: Path) -> None:
    permitted = validate_claim(
        ClaimRequest(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=AvailabilityStatus.AVAILABLE,
            evidence_decision=EvidenceDecision.SUPPORTED,
            anchor_gate_passed=True,
            traffic_rate_available=False,
            wording="Local calibration reduced cross-client FPR dispersion.",
        )
    )
    blocked = validate_claim(
        ClaimRequest(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
            metric=MetricId.TRUE_POSITIVE_RATE,
            availability=AvailabilityStatus.AVAILABLE,
            evidence_decision=EvidenceDecision.BOUNDARY,
            anchor_gate_passed=True,
            traffic_rate_available=False,
            wording="Edge clients improved attack detection.",
        )
    )
    table = PublicationTable(
        title="External boundary",
        cells=(
            TableCell(
                metric=MetricId.FALSE_POSITIVE_RATE,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value="0.125",
                evidence="held-out benign evaluation",
            ),
            TableCell(
                metric=MetricId.TRUE_POSITIVE_RATE,
                availability=AvailabilityStatus.UNAVAILABLE,
                rendered_value="",
                evidence="client-level attack assignment is unavailable",
            ),
        ),
    )
    bundle = PublicationBundle(claims=(permitted, blocked), tables=(table,), figures=())
    destination = tmp_path / "report.md"

    first = export_markdown(bundle, destination).read_text(encoding="utf-8")
    second = export_markdown(bundle, destination).read_text(encoding="utf-8")

    assert permitted.status is ClaimStatus.PERMITTED
    assert blocked.status is ClaimStatus.BLOCKED
    assert first == second
    assert permitted.wording in first
    assert blocked.reason in first
    assert "| true_positive_rate | unavailable |" in first
    assert "| true_positive_rate | 0" not in first
