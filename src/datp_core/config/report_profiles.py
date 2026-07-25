"""Report-profile configuration schema: how a report profile/column/default is structured.

This is report-authoring *configuration* schema, not a reporting-execution feature, so it lives
under ``datp_core.config`` rather than ``datp_core.reporting`` -- keeping it under ``reporting``
previously made every data/learning/thresholding/evaluation handler that transitively imports
``ResolvedProjectConfiguration`` also transitively import the reporting package, violating this
repository's own layering contract (`importlinter.ini`'s
``data-thresholding-evaluation-do-not-import-downstream-features``). Kept as its own leaf module
(rather than merged into `config.models`) so both `config.models` and
`config.resolution.protocols` can depend on it without a circular import between them.
"""

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
    analysis_defined_direction_token: str


__all__ = ["ReportColumnRecord", "ReportDefaultsRecord", "ReportProfileRecord"]
