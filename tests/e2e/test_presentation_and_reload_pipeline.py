from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AvailabilityStatus,
    ClaimWording,
    EvidenceRole,
    ExperimentId,
    MetricId,
    PopulationId,
)
from datp_core.presentation.export import PublicationBundle, ReportProvenance, export_markdown
from datp_core.presentation.tables import EvidenceText, PublicationTable, TableCell, TableTitle
from datp_core.presentation.validation import (
    ClaimKind,
    ClaimRequest,
    ClaimStatus,
    EvidenceDecision,
    validate_claim,
)


def test_presentation_export_is_deterministic_and_preserves_provenance_and_unavailable_outcomes(
    tmp_path: Path,
) -> None:
    blocked_confirmatory = validate_claim(
        ClaimRequest(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=AvailabilityStatus.AVAILABLE,
            evidence_decision=EvidenceDecision.SUPPORTED,
            verified_anchor_gate=None,
            traffic_rate_available=False,
            wording=ClaimWording("Local calibration reduced cross-client FPR dispersion."),
        )
    )
    permitted = validate_claim(
        ClaimRequest(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=AvailabilityStatus.AVAILABLE,
            evidence_decision=EvidenceDecision.SUPPORTED,
            verified_anchor_gate=None,
            traffic_rate_available=False,
            wording=ClaimWording("Supportive threshold construction sensitivity remains claim-bounded."),
        )
    )
    blocked = validate_claim(
        ClaimRequest(
            kind=ClaimKind.EXTERNAL,
            evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
            metric=MetricId.TRUE_POSITIVE_RATE,
            availability=AvailabilityStatus.AVAILABLE,
            evidence_decision=EvidenceDecision.BOUNDARY,
            verified_anchor_gate=None,
            traffic_rate_available=False,
            wording=ClaimWording("Edge clients improved attack detection."),
        )
    )
    table = PublicationTable(
        title=TableTitle("External boundary"),
        cells=(
            TableCell(
                metric=MetricId.FALSE_POSITIVE_RATE,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value="0.125",
                evidence=EvidenceText("held-out benign evaluation"),
            ),
            TableCell(
                metric=MetricId.TRUE_POSITIVE_RATE,
                availability=AvailabilityStatus.UNAVAILABLE,
                rendered_value="",
                evidence=EvidenceText("client-level attack assignment is unavailable"),
            ),
        ),
    )
    provenance = ReportProvenance(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        evidence_role=EvidenceRole.CONFIRMATORY,
        analysis_checksum=Checksum.from_text("validated-analysis"),
    )
    bundle = PublicationBundle(
        provenance=provenance,
        claims=(permitted, blocked, blocked_confirmatory),
        tables=(table,),
        figures=(),
    )
    destination = tmp_path / "report.md"

    first = export_markdown(bundle, destination).read_text(encoding="utf-8")
    second = export_markdown(bundle, destination).read_text(encoding="utf-8")

    assert permitted.status is ClaimStatus.PERMITTED
    assert blocked.status is ClaimStatus.BLOCKED
    assert blocked_confirmatory.status is ClaimStatus.BLOCKED
    assert first == second
    assert provenance.analysis_checksum.value in first
    assert provenance.experiment.value in first
    assert provenance.evidence_role.value in first
    assert permitted.wording in first
    assert blocked.reason in first
    assert "anchor-gate artifact" in blocked_confirmatory.reason
    assert "| true_positive_rate | unavailable |" in first
    assert "| true_positive_rate | 0" not in first
