"""Typed publication-table construction with explicit unavailable cells."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.core.identifiers import AvailabilityStatus, MetricId


@dataclass(frozen=True, slots=True, kw_only=True)
class TableCell:
    metric: MetricId
    availability: AvailabilityStatus
    rendered_value: str
    evidence: str

    def __post_init__(self) -> None:
        if not self.evidence.strip():
            raise ValueError("table cells require evidence")
        if self.availability is not AvailabilityStatus.AVAILABLE and self.rendered_value:
            raise ValueError("unavailable table cells must not contain fabricated values")


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationTable:
    title: str
    cells: tuple[TableCell, ...]

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.cells:
            raise ValueError("publication tables require a title and cells")
        metrics = tuple(cell.metric for cell in self.cells)
        if len(metrics) != len(frozenset(metrics)):
            raise ValueError("publication table metrics must be unique")


def render_markdown_table(table: PublicationTable) -> str:
    rows = ["| Metric | Value | Evidence |", "|---|---:|---|"]
    rows.extend(
        f"| {cell.metric.value} | {cell.rendered_value if cell.rendered_value else cell.availability.value} | "
        f"{cell.evidence} |"
        for cell in table.cells
    )
    return "\n".join((f"### {table.title}", "", *rows, ""))
