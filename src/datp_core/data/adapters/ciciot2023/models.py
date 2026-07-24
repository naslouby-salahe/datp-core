"""CICIoT2023 adapter models."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.data.sources.models import SourceRow


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023RowIdentity:
    client_id: str
    is_attack: bool
    source_path: Path
    source_row_index: int


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023MaterializedRow:
    identity: CICIoT2023RowIdentity
    multiclass_label: str
    source_row: SourceRow


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023DeduplicationResult:
    canonical_rows: tuple[CICIoT2023MaterializedRow, ...]
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023SplitRows:
    train: tuple[CICIoT2023MaterializedRow, ...]
    calibration: tuple[CICIoT2023MaterializedRow, ...]
    test: tuple[CICIoT2023MaterializedRow, ...]
    deduplication: CICIoT2023DeduplicationResult


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023MaterializationReport:
    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int
    duplicate_rows_removed: int
    conflicting_label_feature_group_count: int
    written_rows: int
