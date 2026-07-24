"""Render every configured table/figure from a frozen result manifest: Markdown/LaTeX table
rendering, PNG/PDF figure rendering, and the top-level report-rendering entry point that ties
both together with ``freezing.py`` for the manifest decode and error type.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from io import BytesIO

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from datp_core.reporting.freezing import ResultFreezeError, decode_manifest

# --- shared helpers -------------------------------------------------------------------------


def _records(profile: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    values = profile[key]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError(f"Report profile has malformed {key}")
    return values


# --- table rendering -------------------------------------------------------------------------


def render_table(profile: Mapping[str, object], results: list[Mapping[str, object]]) -> dict[str, object]:
    columns = _records(profile, "columns")
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


# --- figure rendering ------------------------------------------------------------------------


def render_figure(profile: Mapping[str, object], results: list[Mapping[str, object]]) -> dict[str, object]:
    series = _records(profile, "series")
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


def _save_figure(figure: Figure, output_format: str) -> bytes:
    output = BytesIO()
    figure.savefig(output, format=output_format, dpi=144, metadata={"Creator": "datp-core"})
    return output.getvalue()


# --- report rendering entry point ------------------------------------------------------------


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


__all__ = ["render_figure", "render_frozen_report", "render_table"]
