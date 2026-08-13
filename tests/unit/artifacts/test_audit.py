from __future__ import annotations

from pathlib import Path

import pytest
from tools.reproducibility.audit import (
    AUDIT_REPORT_FILENAME,
    AuditRecord,
    AuditReport,
    AuditStatus,
    read_audit_report,
    write_audit_report,
)

from datp_core.core.errors import ArtifactIntegrityError


def test_audit_report_round_trip_preserves_typed_roadmap_status_and_evidence(tmp_path: Path) -> None:
    path = tmp_path / AUDIT_REPORT_FILENAME
    report = AuditReport(
        records=(
            AuditRecord(
                requirement_id="PROVENANCE-018",
                status=AuditStatus.PASS,
                reason="roadmap snapshot and revision are retained",
                evidence_paths=(Path("ROADMAP_LOCK.md"),),
            ),
            AuditRecord(
                requirement_id="REPORT-045",
                status=AuditStatus.UNAVAILABLE_AS_SPECIFIED,
                reason="campaign has not been materialized",
                evidence_paths=(),
            ),
        )
    )

    write_audit_report(path, report)

    assert read_audit_report(path) == report


def test_audit_report_rejects_a_passing_record_without_evidence(tmp_path: Path) -> None:
    report = AuditReport(
        records=(
            AuditRecord(
                requirement_id="PROVENANCE-018",
                status=AuditStatus.PASS,
                reason="invalid",
                evidence_paths=(),
            ),
        )
    )

    with pytest.raises(ArtifactIntegrityError, match="passing audit record requires retained evidence"):
        write_audit_report(tmp_path / AUDIT_REPORT_FILENAME, report)
