"""Markdown/LaTeX table rendering from a frozen result manifest."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from datp_core.reporting.freezing import ResultFreezeError


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


def _records(profile: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    values = profile[key]
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ResultFreezeError(f"Report profile has malformed {key}")
    return values


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


__all__ = ["render_table"]
