"""Report profile configuration schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReportColumnRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    unit: str
    direction: str


class ReportProfileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: str
    artifact_type: str
    table_type: str | None
    figure_type: str | None
    estimate_basis: str | None
    columns: tuple[ReportColumnRecord, ...] | None
    series: tuple[ReportColumnRecord, ...] | None


class ReportDefaultsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    ordering: str
    missing_value_policy: str
    table_output_formats: tuple[str, ...]
    figure_output_formats: tuple[str, ...]
    analysis_defined_direction_token: str


__all__ = ["ReportColumnRecord", "ReportDefaultsRecord", "ReportProfileRecord"]
