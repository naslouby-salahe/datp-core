"""CICIoT2023 adapter models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.data.sources.models import SourceRow


class CICIoT2023RowIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)
    client_id: str
    is_attack: bool
    source_path: Path
    source_row_index: int


class CICIoT2023MaterializedRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    identity: CICIoT2023RowIdentity
    multiclass_label: str
    source_row: SourceRow


class CICIoT2023DeduplicationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    canonical_rows: tuple[CICIoT2023MaterializedRow, ...]
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int


class CICIoT2023SplitRows(BaseModel):
    model_config = ConfigDict(frozen=True)
    train: tuple[CICIoT2023MaterializedRow, ...]
    calibration: tuple[CICIoT2023MaterializedRow, ...]
    test: tuple[CICIoT2023MaterializedRow, ...]
    deduplication: CICIoT2023DeduplicationResult


class CICIoT2023MaterializationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int
    written_rows: int
