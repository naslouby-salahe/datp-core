"""Edge-IIoTset adapter models."""

from __future__ import annotations

from pathlib import Path

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetRow:
    client_id: str | None
    is_attack: bool
    source_path: Path
    source_row_index: int
    numeric_values: tuple[float, ...]
    categorical_values: tuple[str | None, ...]
    multiclass_label: str
    time_of_day_seconds: float | None = None


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetSplitRows:
    train: tuple[EdgeIIoTsetRow, ...]
    calibration: tuple[EdgeIIoTsetRow, ...]
    test: tuple[EdgeIIoTsetRow, ...]
    unassigned_attack: tuple[EdgeIIoTsetRow, ...]
    duplicate_rows_removed: int
    recalibration_reference: tuple[EdgeIIoTsetRow, ...] = ()


@define(frozen=True, slots=True, kw_only=True)
class EdgeTimestampedRow:
    row: EdgeIIoTsetRow
    time_of_day_seconds: float


@define(frozen=True, slots=True, kw_only=True)
class EdgeChronologicalSplitRows:
    historical_train: tuple[EdgeIIoTsetRow, ...]
    historical_calibration: tuple[EdgeIIoTsetRow, ...]
    future_recalibration: tuple[EdgeIIoTsetRow, ...]
    future_evaluation: tuple[EdgeIIoTsetRow, ...]
    excluded_clients: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetVocabulary:
    categories_by_column: tuple[tuple[str, tuple[str, ...]], ...]


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetNormalization:
    minimums: tuple[float, ...]
    maximums: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetExternalIndexReport:
    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int


@define(frozen=True, slots=True, kw_only=True)
class EdgeMaterializationEvidence:
    split_method: str
    excluded_clients: tuple[str, ...]
    chronology_validation: str | None = None


type EdgeIIoTsetSourceResult = (
    EdgeIIoTsetRow  # SourceRowFailure represented upstream; this alias scoped to successful rows
)
