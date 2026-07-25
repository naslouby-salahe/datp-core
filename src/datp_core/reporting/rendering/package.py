"""Top-level report rendering — renders every configured table/figure from a frozen manifest."""

from __future__ import annotations

import json
from collections.abc import Mapping

from datp_core.reporting.freezing.codec import decode_manifest
from datp_core.reporting.freezing.errors import ResultFreezeError
from datp_core.reporting.freezing.models import FrozenReportProfile
from datp_core.reporting.rendering.figures import render_figure
from datp_core.reporting.rendering.tables import render_table


def render_frozen_report(frozen_manifest: bytes) -> bytes:
    """Render every configured table or figure from a previously frozen manifest only."""
    manifest = decode_manifest(frozen_manifest)
    results = _results(manifest)
    rendered = [
        render_figure(_profile_to_dict(profile), results)
        if profile.artifact_type == "figure"
        else render_table(_profile_to_dict(profile), results)
        for profile in manifest.report_profiles
    ]
    return json.dumps(
        {
            "schema_version": 1,
            "experiment_id": manifest.experiment_id,
            "result_freeze_scientific_fingerprint": manifest.scientific_fingerprint,
            "source_files": [
                {"relative_path": source.relative_path, "role": source.role} for source in manifest.source_files
            ],
            "rendered_artifacts": rendered,
        },
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _profile_to_dict(profile: FrozenReportProfile) -> dict[str, object]:
    return {
        "identifier": profile.identifier,
        "artifact_type": profile.artifact_type,
        "table_type": profile.table_type,
        "figure_type": profile.figure_type,
        "estimate_basis": profile.estimate_basis,
        "columns": [
            {"name": column.name, "unit": column.unit, "direction": column.direction} for column in profile.columns
        ],
        "series": [
            {"name": column.name, "unit": column.unit, "direction": column.direction} for column in profile.series
        ],
    }


def _results(manifest) -> list[Mapping[str, object]]:
    values = manifest.statistical_results
    result_list: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, dict):
            raise ResultFreezeError("Result-freeze artifact has malformed statistical results")
        result_list.append(value)
    return result_list


__all__ = ["render_frozen_report"]
