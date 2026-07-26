"""Materialized readiness assessment — schema, client, chronology, and attack checks."""

from __future__ import annotations

from datp_core.core.hashing import Checksum
from datp_core.data.contracts.dataset import DatasetSetup, ResolvedDataset
from datp_core.data.contracts.enums import SplitMembership
from datp_core.data.manifests.models import MaterializedSplitEvidence
from datp_core.data.readiness.models import DatasetAuditIssue, DatasetReadinessReport


class _MaterializedReadinessAssessor:
    """Separated readiness logic for materialized evidence."""

    @staticmethod
    def assess(
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
                    message=(
                        f"Expected {int(expected_client_count)} clients, observed {len(manifest.client_ids)}"),
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
        timestamp_valid = all(
            entry.chronology_key is not None for entry in manifest.entries) if temporal else None
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
