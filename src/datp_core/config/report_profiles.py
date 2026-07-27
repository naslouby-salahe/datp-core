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
