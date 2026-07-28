"""Source-tree and dataset-layout readiness assessment."""

from __future__ import annotations

import csv
from pathlib import Path

from datp_core.data.contracts.enums import AuditIssueCode, AuditSeverity, SourceRole
from datp_core.data.contracts.sources import (
    CICIoT2023SourceConfig,
    DatasetSourceConfig,
    EdgeIIoTsetSourceConfig,
    NBaIoTSourceConfig,
    SourceTreeConfig,
)
from datp_core.data.readiness.models import DatasetAuditIssue, SourceAuditReport, SourceTreeAudit
from datp_core.data.sources.models import SourceInventory


def assess_source_readiness(source: DatasetSourceConfig, inventory: SourceInventory) -> SourceAuditReport:
    issues: list[DatasetAuditIssue] = []
    audits: list[SourceTreeAudit] = []
    for tree in _trees(source):
        entries = tuple(entry for entry in inventory.entries if entry.source_tree_id == tree.identifier)
        audits.append(
            SourceTreeAudit(
                source_tree_id=tree.identifier.value,
                file_count=len(entries),
                executable=tree.role is SourceRole.EXECUTABLE,
            )
        )
        if not entries:
            issues.append(
                DatasetAuditIssue(
                    code=(
                        AuditIssueCode.NO_SOURCE_FILES
                        if tree.role is SourceRole.EXECUTABLE
                        else AuditIssueCode.AUDIT_SOURCE_MISSING
                    ),
                    severity=(AuditSeverity.BLOCKING if tree.role is SourceRole.EXECUTABLE else AuditSeverity.WARNING),
                    detail=f"source tree '{tree.identifier.value}' contains no matching files",
                )
            )
            continue
        headers: list[tuple[str, ...]] = []
        for entry in entries:
            observed = _read_header(entry.source_path)
            headers.append(observed)
            expected = tuple(column.value for column in tree.required_headers)
            if len(observed) != int(tree.expected_column_count) or any(column not in observed for column in expected):
                issues.append(
                    DatasetAuditIssue(
                        code=AuditIssueCode.SOURCE_HEADER_MISMATCH,
                        severity=AuditSeverity.BLOCKING,
                        detail=(
                            f"source '{entry.relative_path.as_posix()}' has {len(observed)} columns; "
                            f"expected {int(tree.expected_column_count)} and all required headers"
                        ),
                    )
                )
        if tree.headers_must_be_identical and len(frozenset(headers)) > 1:
            issues.append(
                DatasetAuditIssue(
                    code=AuditIssueCode.SOURCE_HEADER_MISMATCH,
                    severity=AuditSeverity.BLOCKING,
                    detail=f"source tree '{tree.identifier.value}' contains non-identical headers",
                )
            )
    issues.extend(_layout_issues(source, inventory))
    return SourceAuditReport(tree_audits=tuple(audits), issues=tuple(issues))


def _trees(source: DatasetSourceConfig) -> tuple[SourceTreeConfig, ...]:
    if isinstance(source, CICIoT2023SourceConfig | NBaIoTSourceConfig):
        return (source.tree,)
    if isinstance(source, EdgeIIoTsetSourceConfig):
        return source.benign_trees + source.attack_reference_trees
    raise TypeError(f"unsupported source contract: {type(source).__name__}")


def _layout_issues(source: DatasetSourceConfig, inventory: SourceInventory) -> tuple[DatasetAuditIssue, ...]:
    issues: list[DatasetAuditIssue] = []
    if isinstance(source, NBaIoTSourceConfig):
        tree_root = (inventory.raw_data_root / source.tree.root.value).resolve()
        excluded = tuple(client.value for client in source.excluded_device_directories)
        for client in source.device_directories:
            if client.value in excluded:
                continue
            device_root = tree_root / client.value
            if not device_root.is_dir():
                issues.append(
                    DatasetAuditIssue(
                        code=AuditIssueCode.NO_SOURCE_FILES,
                        severity=AuditSeverity.BLOCKING,
                        detail=f"configured N-BaIoT device directory '{client.value}' is missing",
                    )
                )
                continue
            if source.benign_file_required_per_device and not (device_root / source.benign_filename).is_file():
                issues.append(
                    DatasetAuditIssue(
                        code=AuditIssueCode.NO_SOURCE_FILES,
                        severity=AuditSeverity.BLOCKING,
                        detail=f"N-BaIoT device '{client.value}' lacks its required benign file",
                    )
                )
            if source.attack_family_required_per_device:
                for family in source.attack_family_directories:
                    if not (device_root / family.value).is_dir():
                        issues.append(
                            DatasetAuditIssue(
                                code=AuditIssueCode.NO_SOURCE_FILES,
                                severity=AuditSeverity.BLOCKING,
                                detail=(
                                    f"N-BaIoT device '{client.value}' lacks attack-family directory '{family.value}'"
                                ),
                            )
                        )
    if isinstance(source, EdgeIIoTsetSourceConfig):
        observed: list[str] = []
        for entry in inventory.executable_entries:
            tree = next((item for item in source.benign_trees if item.identifier == entry.source_tree_id), None)
            if tree is None:
                continue
            tree_root = (inventory.raw_data_root / tree.root.value).resolve()
            relative = entry.source_path.relative_to(tree_root)
            component = source.client_identity.component_index
            if component < len(relative.parts):
                observed.append(relative.parts[component])
        observed_clients = frozenset(observed)
        excluded = frozenset(client.value for client in source.excluded_clients)
        for client in source.expected_clients:
            if client.value not in excluded and client.value not in observed_clients:
                issues.append(
                    DatasetAuditIssue(
                        code=AuditIssueCode.NO_SOURCE_FILES,
                        severity=AuditSeverity.BLOCKING,
                        detail=f"configured Edge-IIoTset client '{client.value}' has no executable source files",
                    )
                )
    return tuple(issues)


def _read_header(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        try:
            return tuple(next(reader))
        except StopIteration:
            return ()
