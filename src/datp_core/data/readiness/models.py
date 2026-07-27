"""Readiness audit and report models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import DatasetId, DatasetSetupId


class DatasetAuditIssue(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    code: str
    message: str
    path: Path | None


class SourceTreeAudit(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    identifier: str
    root: Path
    configured_file_pattern: str
    expected_column_count: int
    file_count: int
    header_count: int
    headers_identical: bool


class DatasetAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    dataset_id: DatasetId
    display_name: str
    schema_id: str
    raw_source_found: bool
    file_count: int
    readable: bool
    resolved_root_path: Path
    setup_count: int
    materialization_count: int
    source_trees: tuple[SourceTreeAudit, ...]
    issues: tuple[DatasetAuditIssue, ...]

    @property
    def ready_for_materialization(self) -> bool:
        return self.raw_source_found and self.readable and not self.issues


class DatasetReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    source_fingerprint: Checksum
    schema_summary: tuple[tuple[str, str], ...]
    client_row_counts: dict[str, int]
    class_counts: dict[str, int]
    metadata_availability: dict[str, bool]
    projected_eligible_client_ids: tuple[str, ...]
    attack_evaluable: bool
    timestamp_valid: bool | None
    blocking_defects: tuple[DatasetAuditIssue, ...]

    @property
    def ready_for_training(self) -> bool:
        return not self.blocking_defects

    def encode(self) -> bytes:
        return json.dumps(
            {
                "schema_version": 1,
                "dataset_id": self.dataset_id.value,
                "setup_id": self.setup_id.value,
                "source_fingerprint": self.source_fingerprint.value,
                "schema_summary": self.schema_summary,
                "client_row_counts": self.client_row_counts,
                "class_counts": self.class_counts,
                "metadata_availability": self.metadata_availability,
                "projected_eligible_client_ids": self.projected_eligible_client_ids,
                "attack_evaluable": self.attack_evaluable,
                "timestamp_valid": self.timestamp_valid,
                "blocking_defects": [
                    {
                        "code": defect.code,
                        "message": defect.message,
                        "path": None if defect.path is None else str(defect.path),
                    }
                    for defect in self.blocking_defects
                ],
                "ready_for_training": self.ready_for_training,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
