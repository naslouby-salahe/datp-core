"""Publication figure specifications that cannot invent unavailable series."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.enums import AvailabilityStatus, MetricId


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSeries:
    label: str
    metric: MetricId
    availability: AvailabilityStatus
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("figure series require a label")
        if self.availability is not AvailabilityStatus.AVAILABLE and self.values:
            raise ValueError("unavailable figure series cannot contain values")
        if self.availability is AvailabilityStatus.AVAILABLE and not self.values:
            raise ValueError("available figure series require values")


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSpec:
    title: str
    series: tuple[FigureSeries, ...]

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.series:
            raise ValueError("figure specifications require a title and series")


def render_markdown_figure(figure: FigureSpec) -> str:
    """Render every validated figure series as explicit publication evidence."""
    rows = [
        f"### {figure.title}",
        "",
        "| Series | Metric | Availability | Values |",
        "| --- | --- | --- | --- |",
    ]
    rows.extend(_render_series(series) for series in figure.series)
    return "\n".join(rows)


def _render_series(series: FigureSeries) -> str:
    values = ", ".join(format(value, ".17g") for value in series.values) if series.values else "—"
    return (
        f"| {series.label} | `{series.metric.value}` | `{series.availability.value}` | {values} |"
    )
