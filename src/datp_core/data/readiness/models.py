"""Typed source, materialized, and gate readiness evidence."""

from __future__ import annotations

import msgspec

from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    AuditIssueCode,
    AuditSeverity,
    ReadinessGateFailureCode,
)


class DatasetAuditIssue(msgspec.Struct, frozen=True):
    code: AuditIssueCode
    severity: AuditSeverity
    detail: str


class SourceTreeAudit(msgspec.Struct, frozen=True):
    source_tree_id: str
    file_count: int
    executable: bool


class SourceAuditReport(msgspec.Struct, frozen=True):
    tree_audits: tuple[SourceTreeAudit, ...]
    issues: tuple[DatasetAuditIssue, ...]

    @property
    def blocking_issues(self) -> tuple[DatasetAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is AuditSeverity.BLOCKING)


class MaterializedAuditReport(msgspec.Struct, frozen=True):
    issues: tuple[DatasetAuditIssue, ...]

    @property
    def blocking_issues(self) -> tuple[DatasetAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is AuditSeverity.BLOCKING)


class DatasetReadinessReport(msgspec.Struct, frozen=True):
    schema_version: str
    source: SourceAuditReport
    materialized: MaterializedAuditReport

    @property
    def blocking_issues(self) -> tuple[DatasetAuditIssue, ...]:
        return self.source.blocking_issues + self.materialized.blocking_issues

    @property
    def ready_for_training(self) -> bool:
        return not self.blocking_issues


class ReadinessGateFailure(msgspec.Struct, frozen=True):
    gate_id: str
    code: ReadinessGateFailureCode
    detail: str


def build_readiness_report(
    source: SourceAuditReport,
    materialized: MaterializedAuditReport,
) -> DatasetReadinessReport:
    return DatasetReadinessReport(
        schema_version=ArtifactSchemaVersion.READINESS_V1.value,
        source=source,
        materialized=materialized,
    )


def encode_readiness_report(report: DatasetReadinessReport) -> bytes:
    return msgspec.json.encode(report)
