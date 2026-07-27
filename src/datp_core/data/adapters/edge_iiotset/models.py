"""Edge-IIoTset adapter models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class EdgeIIoTsetRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    client_id: str | None
    is_attack: bool
    source_path: Path
    source_row_index: int
    numeric_values: tuple[float, ...]
    categorical_values: tuple[str | None, ...]
    multiclass_label: str
    time_of_day_seconds: float | None = None


class EdgeIIoTsetSplitRows(BaseModel):
    model_config = ConfigDict(frozen=True)
    train: tuple[EdgeIIoTsetRow, ...]
    calibration: tuple[EdgeIIoTsetRow, ...]
    test: tuple[EdgeIIoTsetRow, ...]
    unassigned_attack: tuple[EdgeIIoTsetRow, ...]
    duplicate_rows_removed: int
    recalibration_reference: tuple[EdgeIIoTsetRow, ...] = ()


class EdgeTimestampedRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    row: EdgeIIoTsetRow
    time_of_day_seconds: float


class EdgeChronologicalSplitRows(BaseModel):
    model_config = ConfigDict(frozen=True)
    historical_train: tuple[EdgeIIoTsetRow, ...]
    historical_calibration: tuple[EdgeIIoTsetRow, ...]
    future_recalibration: tuple[EdgeIIoTsetRow, ...]
    future_evaluation: tuple[EdgeIIoTsetRow, ...]
    excluded_clients: tuple[str, ...]


class EdgeIIoTsetVocabulary(BaseModel):
    model_config = ConfigDict(frozen=True)
    categories_by_column: tuple[tuple[str, tuple[str, ...]], ...]


class EdgeIIoTsetNormalization(BaseModel):
    model_config = ConfigDict(frozen=True)
    minimums: tuple[float, ...]
    maximums: tuple[float, ...]


class EdgeIIoTsetExternalIndexReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int


class EdgeMaterializationEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    split_method: str
    excluded_clients: tuple[str, ...]
    chronology_validation: str | None = None


type EdgeIIoTsetSourceResult = (
    EdgeIIoTsetRow  # SourceRowFailure represented upstream; this alias scoped to successful rows
)
