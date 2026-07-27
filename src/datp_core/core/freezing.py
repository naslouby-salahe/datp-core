from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.reporting.profiles.enums import ReportArtifactType, ReportFigureType, ReportTableType


class FrozenSourceFile(BaseModel):
    model_config = ConfigDict(frozen=True)
    relative_path: str
    role: str


class FrozenReportColumn(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    unit: str
    direction: str


class FrozenReportProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    identifier: str
    artifact_type: ReportArtifactType
    table_type: ReportTableType | None = None
    figure_type: ReportFigureType | None = None
    estimate_basis: str | None = None
    columns: tuple[FrozenReportColumn, ...] = ()
    series: tuple[FrozenReportColumn, ...] = ()


class FrozenResultManifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: int = 1
    experiment_id: str
    evidence_role: str = ""
    dataset_id: str | None = None
    population_ids: tuple[str, ...] = ()
    seed_cohort_id: str = ""
    seed_count: int = 0
    seeds_present: tuple[int, ...] = ()
    scientific_fingerprint: str
    execution_fingerprint: str
    source_revision: str = ""
    frozen_at: str
    metric_definition_version: str = ""
    statistical_procedure_version: str = ""
    report_profiles: tuple[FrozenReportProfile, ...] = ()
    source_files: tuple[FrozenSourceFile, ...] = ()
    statistical_results: tuple[dict[str, object], ...] = ()


