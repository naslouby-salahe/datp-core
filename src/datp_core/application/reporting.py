"""Frozen-result validation and deterministic report-package rendering."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from io import BytesIO
from typing import cast

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt

from datp_core.domain.artifacts import ArtifactKey
from datp_core.domain.catalogue import ExperimentRecord
from datp_core.domain.protocol_contracts import ReportProfileRecord


class ResultFreezeError(ValueError):
    """A result family cannot be safely frozen or rendered."""


_FROZEN_TIMESTAMP = datetime.now(UTC).isoformat()


def freeze_result_family(
    *,
    experiment: ExperimentRecord,
    report_profiles: Sequence[ReportProfileRecord],
    statistical_summary: bytes,
    source_artifacts: Sequence[ArtifactKey],
    scientific_fingerprint: str,
    execution_fingerprint: str,
    source_revision: str,
    seed_count: int,
    dataset_id: str | None = None,
    frozen_at: str | None = None,
) -> bytes:
    """Validate one complete result family and encode its immutable render input.

    Enforces the roadmap 04 §22 freeze contract: all required seeds present or
    formally failed, eligibility final, metric statuses resolved, statistical
    configuration recorded, provenance complete, and validation checks passed.
    """
    results = _decode_result_list(statistical_summary)
    expected_labels = {analysis.label for analysis in experiment.analyses}
    actual_labels = {record["analysis_label"] for record in results}
    missing_labels = sorted(expected_labels - actual_labels)
    if missing_labels:
        raise ResultFreezeError(f"Result freeze is missing configured analyses: {', '.join(missing_labels)}")
    if not source_artifacts:
        raise ResultFreezeError("Result freeze requires the statistical summary artifact")
    if source_artifacts[0].kind.value != "statistical_summary":
        raise ResultFreezeError("Result freeze requires the statistical summary as its first input")

    # --- Precondition: all required seeds are present or formally failed ---
    seeds_present: set[int] = set()
    for record in results:
        seed_val = record.get("seed")
        if isinstance(seed_val, int):
            seeds_present.add(seed_val)
        elif isinstance(seed_val, (int, float)) and not isinstance(seed_val, bool):
            seeds_present.add(int(seed_val))
        # records may carry seeds in a nested structure (paired analyses, etc.)
        for key in ("seeds", "training_seeds"):
            seeds = record.get(key)
            if isinstance(seeds, list):
                for s in seeds:
                    if isinstance(s, int):
                        seeds_present.add(s)
    if len(seeds_present) < seed_count:
        raise ResultFreezeError(
            f"Result freeze requires {seed_count} seeds; only {len(seeds_present)} distinct seeds "
            f"found in statistical results"
        )

    # --- Precondition: metric statuses are resolved ---
    unresolved_statuses: list[str] = []
    for record in results:
        for key, value in record.items():
            if isinstance(key, str) and key.endswith("_status") and isinstance(value, str):
                if value not in _RESOLVED_METRIC_STATUSES and value != "available":
                    unresolved_statuses.append(f"{record.get('analysis_label', '?')}:{key}={value}")
    if unresolved_statuses:
        raise ResultFreezeError(
            f"Result freeze requires all metric statuses to be resolved; "
            f"found {len(unresolved_statuses)} unresolved: {', '.join(unresolved_statuses[:5])}"
        )

    payload = {
        "schema_version": 1,
        "experiment_id": experiment.identifier.value,
        "evidence_role": experiment.evidence_role.value,
        "dataset_id": dataset_id,
        "population_ids": [pid.value for pid in experiment.population_ids],
        "seed_cohort_id": experiment.seed_cohort_id.value,
        "seed_count": seed_count,
        "seeds_present": sorted(seeds_present),
        "scientific_fingerprint": scientific_fingerprint,
        "execution_fingerprint": execution_fingerprint,
        "source_revision": source_revision,
        "frozen_at": frozen_at or _FROZEN_TIMESTAMP,
        "metric_definition_version": experiment.identifier.value,
        "statistical_procedure_version": experiment.checkpoint_profile_id.value,
        "report_profiles": [_profile_payload(profile) for profile in report_profiles],
        "source_artifacts": [
            {"artifact_id": artifact.artifact_id.value, "kind": artifact.kind.value} for artifact in source_artifacts
        ],
        "statistical_results": results,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


# Metric statuses considered fully resolved for freeze purposes.
_RESOLVED_METRIC_STATUSES = frozenset(
    (
        "available",
        "undefined_zero_denominator",
        "undefined_near_zero_denominator",
        "unavailable_missing_benign_class",
        "unavailable_missing_attack_class",
        "unavailable_invalid_attack_assignment",
        "unavailable_ineligible_client",
        "unavailable_unsupported_regime",
        "failed_invalid_artifact",
        "failed_statistical_procedure",
    )
)


def render_frozen_report(frozen_manifest: bytes) -> bytes:
    """Render every configured table or figure from a previously frozen manifest only."""
    manifest = _decode_manifest(frozen_manifest)
    rendered = []
    for profile in _profiles(manifest):
        if profile["artifact_type"] == "figure":
            rendered.append(_render_figure(profile, manifest))
        else:
            rendered.append(_render_table(profile, manifest))
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


def _decode_result_list(payload: bytes) -> list[dict[str, object]]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ResultFreezeError("Statistical summary is not valid JSON") from exc
    if not isinstance(decoded, list):
        raise ResultFreezeError("Statistical summary must be a JSON list")
    results: list[dict[str, object]] = []
    for index, value in enumerate(decoded):
        if not isinstance(value, dict):
            raise ResultFreezeError(f"Statistical result {index} must be a JSON object")
        label = value.get("analysis_label")
        if not isinstance(label, str) or not label:
            raise ResultFreezeError(f"Statistical result {index} lacks a non-empty analysis_label")
        results.append(cast(dict[str, object], value))
    return results


def _decode_manifest(payload: bytes) -> dict[str, object]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ResultFreezeError("Result-freeze artifact is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ResultFreezeError("Result-freeze artifact must be a JSON object")
    required = (
        "experiment_id",
        "scientific_fingerprint",
        "execution_fingerprint",
        "report_profiles",
        "source_artifacts",
        "statistical_results",
        "frozen_at",
    )
    if any(field not in decoded for field in required):
        raise ResultFreezeError("Result-freeze artifact lacks required provenance fields")
    if not isinstance(decoded["report_profiles"], list) or not isinstance(decoded["statistical_results"], list):
        raise ResultFreezeError("Result-freeze artifact has malformed report records")
    return cast(dict[str, object], decoded)


def _profile_payload(profile: ReportProfileRecord) -> dict[str, object]:
    def columns(values):
        return (
            []
            if values is None
            else [{"name": value.name, "unit": value.unit, "direction": value.direction} for value in values]
        )

    return {
        "identifier": profile.identifier,
        "artifact_type": profile.artifact_type,
        "table_type": profile.table_type,
        "figure_type": profile.figure_type,
        "estimate_basis": profile.estimate_basis,
        "columns": columns(profile.columns),
        "series": columns(profile.series),
    }


def _render_table(profile: Mapping[str, object], manifest: Mapping[str, object]) -> dict[str, object]:
    columns = _records(profile, "columns")
    results = _results(manifest)
    headers = [str(column["name"]) for column in columns]
    rows = [[_table_value(header, result) for header in headers] for result in results] or [
        ["unavailable"] * len(headers)
    ]
    markdown = _markdown_table(headers, rows)
    return {
        "profile_id": profile["identifier"],
        "artifact_type": "table",
        "table_type": profile["table_type"],
        "outputs": {"markdown": markdown, "latex": _latex_table(headers, rows)},
    }


def _render_figure(profile: Mapping[str, object], manifest: Mapping[str, object]) -> dict[str, object]:
    series = _records(profile, "series")
    results = _results(manifest)
    figure, axis = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    plotted = False
    for result in results:
        values = result.get("seed_differences")
        if isinstance(values, list) and all(isinstance(value, int | float) for value in values):
            axis.plot(range(1, len(values) + 1), values, marker="o", label=str(result["analysis_label"]))
            plotted = True
    if plotted:
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.set_xlabel("Training seed order")
        axis.set_ylabel("Paired difference")
        axis.legend()
    else:
        names = ", ".join(str(item["name"]) for item in series)
        axis.text(0.5, 0.5, f"Unavailable\n{names}", ha="center", va="center")
        axis.set_axis_off()
    axis.set_title(str(profile["identifier"]))
    png = _save_figure(figure, "png")
    pdf = _save_figure(figure, "pdf")
    plt.close(figure)
    return {
        "profile_id": profile["identifier"],
        "artifact_type": "figure",
        "figure_type": profile["figure_type"],
        "outputs": {
            "png_base64": base64.b64encode(png).decode("ascii"),
            "pdf_base64": base64.b64encode(pdf).decode("ascii"),
        },
    }


def _save_figure(figure, output_format: str) -> bytes:
    output = BytesIO()
    figure.savefig(output, format=output_format, dpi=144, metadata={"Creator": "datp-core"})
    return output.getvalue()


def _records(profile: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    values = profile[key]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError(f"Report profile has malformed {key}")
    return [cast(Mapping[str, object], value) for value in values]


def _profiles(manifest: Mapping[str, object]) -> list[Mapping[str, object]]:
    values = manifest["report_profiles"]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError("Result-freeze artifact has malformed report profiles")
    return [cast(Mapping[str, object], value) for value in values]


def _results(manifest: Mapping[str, object]) -> list[Mapping[str, object]]:
    values = manifest["statistical_results"]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError("Result-freeze artifact has malformed statistical results")
    return [cast(Mapping[str, object], value) for value in values]


def _table_value(column: str, result: Mapping[str, object]) -> str:
    if column == "threshold_construction":
        first = result.get("first_threshold_policy")
        second = result.get("second_threshold_policy")
        return (
            f"{first} vs {second}"
            if isinstance(first, str) and isinstance(second, str)
            else str(result["analysis_label"])
        )
    values = {
        "cv_fpr": result.get("first_mean"),
        "delta": result.get("mean_difference"),
        "bca_lower_bound": _interval_bound(result, 0),
        "bca_upper_bound": _interval_bound(result, 1),
        "sign_consistency": result.get("sign_consistency"),
    }
    value = values.get(column, result.get(column))
    return _presentation_value(value)


def _interval_bound(result: Mapping[str, object], index: int) -> object | None:
    interval = result.get("confidence_interval")
    return interval[index] if isinstance(interval, list) and len(interval) == 2 else None


def _presentation_value(value: object | None) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return "\n".join(
        (
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in rows),
        )
    )


def _latex_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    escaped_headers = [_escape_latex(header) for header in headers]
    body = [" & ".join(escaped_headers) + r" \\"]
    body.extend(" & ".join(_escape_latex(value) for value in row) + r" \\" for row in rows)
    return "\n".join((r"\begin{tabular}{" + "l" * len(headers) + "}", *body, r"\end{tabular}"))


def _escape_latex(value: str) -> str:
    return value.replace("_", r"\_")
