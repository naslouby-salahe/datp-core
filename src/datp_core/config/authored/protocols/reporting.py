"""Authored reporting-defaults and report-profile contracts (protocols.yaml)."""

from __future__ import annotations

from datp_core.config.authored.base import StrictFrozenConfigModel


class ReportDefaultsConfig(StrictFrozenConfigModel):
    ordering: str
    missing_value_policy: str
    table_output_formats: list[str]
    figure_output_formats: list[str]
    analysis_defined_direction_token: str


class ReportColumnConfig(StrictFrozenConfigModel):
    name: str
    unit: str
    direction: str


class ReportProfileConfig(StrictFrozenConfigModel):
    artifact_type: str
    table_type: str | None = None
    figure_type: str | None = None
    estimate_basis: str | None = None
    columns: list[ReportColumnConfig] | None = None
    series: list[ReportColumnConfig] | None = None
