"""Resolved report-profile and report-defaults contracts (protocols.yaml)."""

from __future__ import annotations

from typing import cast

from attrs import define, field


@define(frozen=True, slots=True, kw_only=True)
class ReportColumnRecord:
    name: str
    unit: str
    direction: str


def _as_optional_report_columns(value: object) -> tuple[ReportColumnRecord, ...] | None:
    if value is None:
        return None
    return cast("tuple[ReportColumnRecord, ...]", tuple(cast("list[ReportColumnRecord]", value)))


@define(frozen=True, slots=True, kw_only=True)
class ReportProfileRecord:
    identifier: str
    artifact_type: str
    table_type: str | None
    figure_type: str | None
    estimate_basis: str | None
    columns: tuple[ReportColumnRecord, ...] | None = field(converter=_as_optional_report_columns)
    series: tuple[ReportColumnRecord, ...] | None = field(converter=_as_optional_report_columns)


@define(frozen=True, slots=True, kw_only=True)
class ReportDefaultsRecord:
    ordering: str
    missing_value_policy: str
    table_output_formats: tuple[str, ...]
    figure_output_formats: tuple[str, ...]
    provenance_required_per_artifact: bool
    analysis_defined_direction_token: str
