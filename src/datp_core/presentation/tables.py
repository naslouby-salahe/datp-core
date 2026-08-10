from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from datp_core.core.identifiers import AvailabilityStatus, MetricId, NonEmptyString, ReportLine


class TableTitle(NonEmptyString):
    validation_name: ClassVar[str] = "table title"


class EvidenceText(NonEmptyString):
    validation_name: ClassVar[str] = "table cell evidence"


class TableCellRenderedValue(str):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TableCell:
    metric: MetricId
    availability: AvailabilityStatus
    rendered_value: TableCellRenderedValue
    evidence: EvidenceText

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceText):
            object.__setattr__(self, "evidence", EvidenceText(self.evidence))
        if not isinstance(self.rendered_value, TableCellRenderedValue):
            object.__setattr__(self, "rendered_value", TableCellRenderedValue(self.rendered_value))
        if self.availability is not AvailabilityStatus.AVAILABLE and self.rendered_value:
            raise ValueError("unavailable table cells must not contain fabricated values")


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationTable:
    title: TableTitle
    cells: tuple[TableCell, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.title, TableTitle):
            object.__setattr__(self, "title", TableTitle(self.title))
        if not self.cells:
            raise ValueError("publication tables require a title and cells")
        metrics = tuple(cell.metric for cell in self.cells)
        if len(metrics) != len(frozenset(metrics)):
            raise ValueError("publication table metrics must be unique")


def render_markdown_table(table: PublicationTable) -> ReportLine:
    rows = ["| Metric | Value | Evidence |", "|---|---:|---|"]
    rows.extend(
        f"| {cell.metric.value} | {cell.rendered_value if cell.rendered_value else cell.availability.value} | "
        f"{cell.evidence} |"
        for cell in table.cells
    )
    return ReportLine("\n".join((f"### {table.title}", "", *rows, "")))
