"""Render every configured table/figure from a frozen result manifest -- the sole module that
imports both ``tables.py`` and ``figures.py`` (mirroring the resolver/validation one-directional
pattern in ``configuration/``), plus ``freezing.py`` for the manifest decode and error type.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from datp_core.reporting.figures import render_figure
from datp_core.reporting.freezing import ResultFreezeError, decode_manifest
from datp_core.reporting.tables import render_table


def render_frozen_report(frozen_manifest: bytes) -> bytes:
    """Render every configured table or figure from a previously frozen manifest only."""
    manifest = decode_manifest(frozen_manifest)
    results = _results(manifest)
    rendered = [
        render_figure(profile, results) if profile["artifact_type"] == "figure" else render_table(profile, results)
        for profile in _profiles(manifest)
    ]
    return json.dumps(
        {
            "schema_version": 1,
            "experiment_id": manifest["experiment_id"],
            "result_freeze_scientific_fingerprint": manifest["scientific_fingerprint"],
            "source_artifacts": manifest["source_artifacts"],
            "rendered_artifacts": rendered,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _profiles(manifest: Mapping[str, object]) -> list[Mapping[str, object]]:
    values = manifest["report_profiles"]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError("Result-freeze artifact has malformed report profiles")
    return values


def _results(manifest: Mapping[str, object]) -> list[Mapping[str, object]]:
    values = manifest["statistical_results"]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError("Result-freeze artifact has malformed statistical results")
    return values


__all__ = ["render_frozen_report"]
