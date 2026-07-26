from __future__ import annotations

import json
from typing import cast

from attrs import define


class FrozenResultDecodeError(ValueError):
    """A frozen result manifest cannot be decoded."""


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


def decode_manifest(payload: bytes) -> FrozenResultManifest:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FrozenResultDecodeError("Result-freeze artifact is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise FrozenResultDecodeError("Result-freeze artifact must be a JSON object")
    required = (
        "experiment_id",
        "scientific_fingerprint",
        "execution_fingerprint",
        "report_profiles",
        "source_files",
        "statistical_results",
        "frozen_at",
    )
    if any(field not in decoded for field in required):
        raise FrozenResultDecodeError("Result-freeze artifact lacks required provenance fields")
    if not isinstance(decoded["report_profiles"], list) or not isinstance(decoded["statistical_results"], list):
        raise FrozenResultDecodeError("Result-freeze artifact has malformed report records")

    profiles = tuple(
        FrozenReportProfile(
            identifier=str(p["identifier"]),
            artifact_type=str(p["artifact_type"]),
            table_type=str(p["table_type"]) if p.get("table_type") is not None else None,
            figure_type=str(p["figure_type"]) if p.get("figure_type") is not None else None,
            estimate_basis=str(p["estimate_basis"]) if p.get("estimate_basis") is not None else None,
            columns=tuple(
                FrozenReportColumn(name=str(c["name"]), unit=str(c["unit"]), direction=str(c["direction"]))
                for c in p.get("columns", [])
            ),
            series=tuple(
                FrozenReportColumn(name=str(c["name"]), unit=str(c["unit"]), direction=str(c["direction"]))
                for c in p.get("series", [])
            ),
        )
        for p in decoded["report_profiles"]
        if isinstance(p, dict)
    )

    source_files = tuple(
        FrozenSourceFile(relative_path=str(a["relative_path"]), role=str(a["role"]))
        for a in decoded["source_files"]
        if isinstance(a, dict)
    )

    return FrozenResultManifest(
        schema_version=int(decoded.get("schema_version", 1)),
        experiment_id=str(decoded["experiment_id"]),
        evidence_role=str(decoded.get("evidence_role", "")),
        dataset_id=str(decoded["dataset_id"]) if decoded.get("dataset_id") is not None else None,
        population_ids=tuple(str(p) for p in decoded.get("population_ids", [])),
        seed_cohort_id=str(decoded.get("seed_cohort_id", "")),
        seed_count=int(decoded.get("seed_count", 0)),
        seeds_present=tuple(int(s) for s in decoded.get("seeds_present", [])),
        scientific_fingerprint=str(decoded["scientific_fingerprint"]),
        execution_fingerprint=str(decoded["execution_fingerprint"]),
        source_revision=str(decoded.get("source_revision", "")),
        frozen_at=str(decoded["frozen_at"]),
        metric_definition_version=str(decoded.get("metric_definition_version", "")),
        statistical_procedure_version=str(decoded.get("statistical_procedure_version", "")),
        report_profiles=profiles,
        source_files=source_files,
        statistical_results=tuple(cast(object, r) for r in decoded["statistical_results"]),
    )
