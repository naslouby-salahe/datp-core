"""Resolution of reporting defaults and report-profile records."""

from __future__ import annotations

from datp_core.config.authored.protocols.reporting import ReportDefaultsConfig, ReportProfileConfig
from datp_core.config.report_profiles import ReportColumnRecord, ReportDefaultsRecord, ReportProfileRecord


def resolve_report_defaults(cfg: ReportDefaultsConfig) -> ReportDefaultsRecord:
    return ReportDefaultsRecord(
        ordering=cfg.ordering,
        missing_value_policy=cfg.missing_value_policy,
        table_output_formats=tuple(cfg.table_output_formats),
        figure_output_formats=tuple(cfg.figure_output_formats),
        analysis_defined_direction_token=cfg.analysis_defined_direction_token,
    )


def resolve_report_profile(identifier: str, cfg: ReportProfileConfig) -> ReportProfileRecord:
    return ReportProfileRecord(
        identifier=identifier,
        artifact_type=cfg.artifact_type,
        table_type=cfg.table_type,
        figure_type=cfg.figure_type,
        estimate_basis=cfg.estimate_basis,
        columns=(
            [ReportColumnRecord(name=c.name, unit=c.unit, direction=c.direction) for c in cfg.columns]
            if cfg.columns is not None
            else None
        ),
        series=(
            [ReportColumnRecord(name=c.name, unit=c.unit, direction=c.direction) for c in cfg.series]
            if cfg.series is not None
            else None
        ),
    )
