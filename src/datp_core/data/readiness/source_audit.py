"""Deterministic source-contract audit: containment, existence, inventory, headers, layout."""

from __future__ import annotations

import csv
from pathlib import Path

from datp_core.core.hashing import Checksum
from datp_core.data.contracts.dataset import DatasetSetup, ResolvedDataset
from datp_core.data.contracts.enums import SplitMembership
from datp_core.data.contracts.sources import ConfiguredSourceTree
from datp_core.data.manifests.models import MaterializedSplitEvidence
from datp_core.data.readiness.models import DatasetAuditIssue, DatasetAuditReport, DatasetReadinessReport, SourceTreeAudit
from datp_core.data.sources.inventory import build_source_inventory


class AuditDatasetUseCase:
    def execute(self, dataset: ResolvedDataset) -> DatasetAuditReport:
        raw_data_root = dataset.paths.raw_data_root.resolve()
        root_path = dataset.paths.raw_root.resolve()
        issues: list[DatasetAuditIssue] = []
        if not root_path.is_relative_to(raw_data_root):
            issues.append(
                DatasetAuditIssue(
                    code="source_root_escapes_raw_data",
                    message="Resolved dataset source root escapes the configured raw-data root",
                    path=root_path,
                )
            )
        if not root_path.exists():
            issues.append(
                DatasetAuditIssue(code="source_root_missing", message="Dataset root is missing", path=root_path)
            )
        elif not root_path.is_dir():
            issues.append(
                DatasetAuditIssue(
                    code="source_root_not_directory", message="Dataset root is not a directory", path=root_path
                )
            )

        source_audits = tuple(
            self._audit_source_tree(dataset, tree, issues) for tree in dataset.inspection_contract.source_trees
        )
        self._audit_required_layout(dataset, issues)
        return DatasetAuditReport(
            dataset_id=dataset.dataset_id,
            display_name=dataset.display_name,
            schema_id=dataset.schema_id,
            raw_source_found=root_path.exists(),
            file_count=sum(tree.file_count for tree in source_audits),
            readable=root_path.is_dir(),
            resolved_root_path=root_path,
            setup_count=len(dataset.setups),
            materialization_count=len(dataset.materializations),
            source_trees=source_audits,
            issues=tuple(issues),
        )

    def _audit_source_tree(
        self,
        dataset: ResolvedDataset,
        tree: ConfiguredSourceTree,
        issues: list[DatasetAuditIssue],
    ) -> SourceTreeAudit:
        raw_data_root = dataset.paths.raw_data_root.resolve()
        source_root = (raw_data_root / tree.root.value).resolve()
        if not source_root.is_relative_to(raw_data_root):
            issues.append(
                DatasetAuditIssue(
                    code="source_tree_escapes_raw_data",
                    message=f"Source tree '{tree.identifier}' escapes the configured raw-data root",
                    path=source_root,
                )
            )
            return SourceTreeAudit(
                identifier=tree.identifier,
                root=source_root,
                configured_file_pattern=tree.file_pattern,
                expected_column_count=tree.expected_column_count,
                file_count=0,
                header_count=0,
                headers_identical=False,
            )
        if not source_root.is_dir():
            issues.append(
                DatasetAuditIssue(
                    code="source_tree_missing",
                    message=f"Configured source tree '{tree.identifier}' is missing",
                    path=source_root,
                )
            )
            return SourceTreeAudit(
                identifier=tree.identifier,
                root=source_root,
                configured_file_pattern=tree.file_pattern,
                expected_column_count=tree.expected_column_count,
                file_count=0,
                header_count=0,
                headers_identical=False,
            )
        files = self._source_files(dataset, tree, source_root)
        if not files:
            issues.append(
                DatasetAuditIssue(
                    code="source_tree_has_no_matching_files",
                    message=f"Source tree '{tree.identifier}' has no files matching '{tree.file_pattern}'",
                    path=source_root,
                )
            )
        headers: list[tuple[str, ...]] = []
        for file_path in files:
            header = self._read_header(file_path, issues)
            if header is None:
                continue
            headers.append(header)
            if len(header) != tree.expected_column_count:
                issues.append(
                    DatasetAuditIssue(
                        code="unexpected_column_count",
                        message=(
                            f"Expected {tree.expected_column_count} columns in source tree '{tree.identifier}', "
                            f"found {len(header)}"
                        ),
                        path=file_path,
                    )
                )
            missing_headers = tuple(header_name for header_name in tree.required_headers if header_name not in header)
            if missing_headers:
                issues.append(
                    DatasetAuditIssue(
                        code="missing_required_headers",
                        message=(
                            f"Source tree '{tree.identifier}' is missing required headers: {', '.join(missing_headers)}"
                        ),
                        path=file_path,
                    )
                )
        headers_identical = len(set(headers)) <= 1
        if dataset.inspection_contract.require_identical_headers and not headers_identical:
            issues.append(
                DatasetAuditIssue(
                    code="headers_not_identical",
                    message=f"Source tree '{tree.identifier}' has non-identical CSV headers",
                    path=source_root,
                )
            )
        return SourceTreeAudit(
            identifier=tree.identifier,
            root=source_root,
            configured_file_pattern=tree.file_pattern,
            expected_column_count=tree.expected_column_count,
            file_count=len(files),
            header_count=len(headers),
            headers_identical=headers_identical,
        )

    def _source_files(
        self, dataset: ResolvedDataset, tree: ConfiguredSourceTree, source_root: Path
    ) -> tuple[Path, ...]:
        contract = dataset.inspection_contract
        if contract.device_directories or contract.normal_group_directories:
            candidates = source_root.rglob("*.csv")
        else:
            candidates = source_root.glob(tree.file_pattern)
        ignored_subtrees = tuple(
            (dataset.paths.raw_data_root / relative_path).resolve()
            for relative_path in dataset.source_layout.ignored_subtrees
        )
        files = (
            path
            for path in candidates
            if path.is_file()
            and path.suffix not in dataset.source_layout.ignored_suffixes
            and not any(path.is_relative_to(ignored) for ignored in ignored_subtrees)
        )
        return tuple(sorted(files, key=lambda path: path.relative_to(dataset.paths.raw_data_root).as_posix()))

    def _audit_required_layout(self, dataset: ResolvedDataset, issues: list[DatasetAuditIssue]) -> None:
        contract = dataset.inspection_contract
        root = dataset.paths.raw_root
        for device_directory in contract.device_directories:
            device_root = root / device_directory
            if not device_root.is_dir():
                issues.append(
                    DatasetAuditIssue(
                        code="missing_device_directory",
                        message=f"Missing device directory '{device_directory}'",
                        path=device_root,
                    )
                )
                continue
            if contract.benign_file_required_per_device and contract.benign_filename is not None:
                benign_path = device_root / contract.benign_filename
                if not benign_path.is_file():
                    issues.append(
                        DatasetAuditIssue(
                            code="missing_benign_file", message="Missing required benign file", path=benign_path
                        )
                    )
            if contract.attack_family_required_per_device:
                for family in contract.attack_family_directories:
                    family_path = device_root / family
                    if not family_path.is_dir():
                        issues.append(
                            DatasetAuditIssue(
                                code="missing_attack_family",
                                message=f"Missing attack family '{family}'",
                                path=family_path,
                            )
                        )
        for group_directory in contract.normal_group_directories:
            group_path = root / "Normal traffic" / group_directory
            if not group_path.is_dir():
                issues.append(
                    DatasetAuditIssue(
                        code="missing_normal_group",
                        message=f"Missing normal group '{group_directory}'",
                        path=group_path,
                    )
                )
        for attack_filename in contract.attack_filenames:
            attack_path = root / "Attack traffic" / attack_filename
            if not attack_path.is_file():
                issues.append(
                    DatasetAuditIssue(
                        code="missing_attack_file",
                        message=f"Missing attack file '{attack_filename}'",
                        path=attack_path,
                    )
                )

    @staticmethod
    def _read_header(path: Path, issues: list[DatasetAuditIssue]) -> tuple[str, ...] | None:
        try:
            with path.open("r", encoding="utf-8", newline="") as source:
                header = next(csv.reader(source), None)
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            issues.append(DatasetAuditIssue(code="unreadable_csv", message=str(exc), path=path))
            return None
        if header is None:
            issues.append(DatasetAuditIssue(code="empty_csv", message="CSV source has no header", path=path))
            return None
        return tuple(header)

    def assess_materialization(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        evidence: MaterializedSplitEvidence,
        source_fingerprint: Checksum,
    ) -> DatasetReadinessReport:
        columns = dict(evidence.schema_columns)
        manifest = evidence.manifest
        defects: list[DatasetAuditIssue] = []
        required_columns = ("split", "client_id", "is_attack", "source_path", "source_row_index")
        missing_columns = tuple(column for column in required_columns if column not in columns)
        if missing_columns:
            defects.append(
                DatasetAuditIssue(
                    code="materialized_schema_missing_required_columns",
                    message=f"Materialized payload is missing required columns: {', '.join(missing_columns)}",
                    path=None,
                )
            )
        if not manifest.eligible_client_ids:
            defects.append(
                DatasetAuditIssue(
                    code="no_eligible_clients",
                    message="No client has the configured benign calibration support",
                    path=None,
                )
            )
        expected_client_count = setup.client_construction.client_count
        if expected_client_count is not None and len(manifest.client_ids) != int(expected_client_count):
            defects.append(
                DatasetAuditIssue(
                    code="unexpected_client_count",
                    message=(f"Expected {int(expected_client_count)} clients, observed {len(manifest.client_ids)}"),
                    path=None,
                )
            )

        temporal = any(
            entry.membership
            in {
                SplitMembership.HISTORICAL_TRAINING,
                SplitMembership.HISTORICAL_CALIBRATION,
                SplitMembership.FUTURE_RECALIBRATION,
                SplitMembership.FUTURE_EVALUATION,
            }
            for entry in manifest.entries
        )
        timestamp_valid = all(entry.chronology_key is not None for entry in manifest.entries) if temporal else None
        if temporal and not timestamp_valid:
            defects.append(
                DatasetAuditIssue(
                    code="invalid_temporal_chronology",
                    message="Temporal materialization lacks a chronology key for one or more rows",
                    path=None,
                )
            )

        capabilities = frozenset(setup.capabilities)
        attack_entries = tuple(entry for entry in manifest.entries if entry.is_attack)
        attack_evaluable = bool(attack_entries) and all(
            entry.client_id in manifest.client_ids for entry in attack_entries
        )
        if "per_client_attack_detection_metrics" in capabilities and not attack_evaluable:
            defects.append(
                DatasetAuditIssue(
                    code="attack_evaluation_unavailable",
                    message="Configured per-client attack detection has no client-assigned attack rows",
                    path=None,
                )
            )

        timestamp_field = dataset.field_schema.identity_scheme.timestamp_field
        return DatasetReadinessReport(
            dataset_id=dataset.dataset_id,
            setup_id=setup.identifier,
            source_fingerprint=source_fingerprint,
            schema_summary=evidence.schema_columns,
            client_row_counts=manifest.client_row_counts,
            class_counts=manifest.class_counts,
            metadata_availability={
                "client": "client_id" in columns,
                "family_taxonomy": dataset.field_schema.label_fields.family_taxonomy is not None,
                "timestamp": temporal or (isinstance(timestamp_field, str) and timestamp_field != "unavailable"),
            },
            projected_eligible_client_ids=manifest.eligible_client_ids,
            attack_evaluable=attack_evaluable,
            timestamp_valid=timestamp_valid,
            blocking_defects=tuple(defects),
        )
