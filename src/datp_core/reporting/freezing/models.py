"""Typed immutable frozen result models."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class FrozenSourceFile:
    relative_path: str
    role: str


@define(frozen=True, slots=True, kw_only=True)
class FrozenReportColumn:
    name: str
    unit: str
    direction: str


@define(frozen=True, slots=True, kw_only=True)
class FrozenReportProfile:
    identifier: str
    artifact_type: str
    table_type: str | None
    figure_type: str | None
    estimate_basis: str | None
    columns: tuple[FrozenReportColumn, ...]
    series: tuple[FrozenReportColumn, ...]


@define(frozen=True, slots=True, kw_only=True)
class FrozenResultManifest:
    schema_version: int
    experiment_id: str
    evidence_role: str
    dataset_id: str | None
    population_ids: tuple[str, ...]
    seed_cohort_id: str
    seed_count: int
    seeds_present: tuple[int, ...]
    scientific_fingerprint: str
    execution_fingerprint: str
    source_revision: str
    frozen_at: str
    metric_definition_version: str
    statistical_procedure_version: str
    report_profiles: tuple[FrozenReportProfile, ...]
    source_files: tuple[FrozenSourceFile, ...]
    statistical_results: tuple[object, ...]
