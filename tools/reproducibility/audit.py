from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage

AUDIT_REPORT_FILENAME = "roadmap_audit.json"


class AuditStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE_AS_SPECIFIED = "UNAVAILABLE_AS_SPECIFIED"


@dataclass(frozen=True, slots=True)
class AuditRecord:
    requirement_id: str
    status: AuditStatus
    reason: str
    evidence_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class AuditReport:
    records: tuple[AuditRecord, ...]


def write_audit_report(path: Path, report: AuditReport) -> None:
    """Write a new, deterministic roadmap-audit record for release retention."""

    _validate_report(report)
    if path.exists():
        raise ArtifactIntegrityError(ErrorMessage(f"audit report destination already exists: {path}"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_report_payload(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_audit_report(path: Path) -> AuditReport:
    """Read and validate an audit report retained in a release bundle."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError(ErrorMessage(f"audit report is unreadable: {path}")) from error
    if not isinstance(payload, dict) or tuple(payload) != ("records",):
        raise ArtifactIntegrityError(ErrorMessage("audit report must contain only the records field"))
    raw_records = payload["records"]
    if not isinstance(raw_records, list):
        raise ArtifactIntegrityError(ErrorMessage("audit report records must be a list"))
    records = tuple(_record_from_payload(record) for record in raw_records)
    report = AuditReport(records=records)
    _validate_report(report)
    return report


def _report_payload(report: AuditReport) -> dict[str, list[dict[str, object]]]:
    return {
        "records": [
            {
                "evidence_paths": [str(path) for path in record.evidence_paths],
                "reason": record.reason,
                "requirement_id": record.requirement_id,
                "status": record.status.value,
            }
            for record in report.records
        ]
    }


def _record_from_payload(payload: object) -> AuditRecord:
    if not isinstance(payload, dict):
        raise ArtifactIntegrityError(ErrorMessage("audit report record must be an object"))
    expected_fields = {"requirement_id", "status", "reason", "evidence_paths"}
    if set(payload) != expected_fields:
        raise ArtifactIntegrityError(ErrorMessage("audit report record fields do not match the locked schema"))
    requirement_id = payload["requirement_id"]
    status = payload["status"]
    reason = payload["reason"]
    evidence_paths = payload["evidence_paths"]
    if not isinstance(requirement_id, str) or not isinstance(status, str) or not isinstance(reason, str):
        raise ArtifactIntegrityError(ErrorMessage("audit report record scalar fields must be strings"))
    if not isinstance(evidence_paths, list) or not all(isinstance(item, str) for item in evidence_paths):
        raise ArtifactIntegrityError(ErrorMessage("audit report evidence paths must be strings"))
    try:
        audit_status = AuditStatus(status)
    except ValueError as error:
        raise ArtifactIntegrityError(ErrorMessage("audit report contains an unknown status")) from error
    return AuditRecord(
        requirement_id=requirement_id,
        status=audit_status,
        reason=reason,
        evidence_paths=tuple(Path(item) for item in evidence_paths),
    )


def _validate_report(report: AuditReport) -> None:
    if not report.records:
        raise ArtifactIntegrityError(ErrorMessage("audit report must contain at least one record"))
    identifiers = tuple(record.requirement_id for record in report.records)
    if identifiers != tuple(sorted(identifiers)):
        raise ArtifactIntegrityError(ErrorMessage("audit report records must be ordered by requirement identifier"))
    if len(identifiers) != len(frozenset(identifiers)):
        raise ArtifactIntegrityError(ErrorMessage("audit report cannot repeat a requirement identifier"))
    for record in report.records:
        if not record.requirement_id or not record.reason:
            raise ArtifactIntegrityError(ErrorMessage("audit report records require an identifier and reason"))
        paths = record.evidence_paths
        if record.status is AuditStatus.PASS and not paths:
            raise ArtifactIntegrityError(ErrorMessage("a passing audit record requires retained evidence"))
        if len(paths) != len(frozenset(paths)):
            raise ArtifactIntegrityError(ErrorMessage("audit report record cannot repeat an evidence path"))
        for evidence_path in paths:
            if evidence_path.is_absolute() or ".." in evidence_path.parts or evidence_path == Path("."):
                raise ArtifactIntegrityError(ErrorMessage("audit report evidence path must be release-relative"))
