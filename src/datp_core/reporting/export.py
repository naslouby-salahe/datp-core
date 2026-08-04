"""Validated publication-export writing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.reporting.figures import FigureSpec
from datp_core.reporting.tables import PublicationTable, render_markdown_table
from datp_core.reporting.validation import ClaimDecision


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationBundle:
    claims: tuple[ClaimDecision, ...]
    tables: tuple[PublicationTable, ...]
    figures: tuple[FigureSpec, ...]


def export_markdown(bundle: PublicationBundle, destination: Path) -> Path:
    blocked = tuple(decision for decision in bundle.claims if decision.wording == "")
    permitted = tuple(decision.wording for decision in bundle.claims if decision.wording)
    sections = ["# DATP-Core Results", ""]
    sections.extend(permitted)
    if blocked:
        sections.extend(("", "## Suppressed or blocked claims", ""))
        sections.extend(f"- {decision.reason}" for decision in blocked)
    for table in bundle.tables:
        sections.extend(("", render_markdown_table(table)))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination
