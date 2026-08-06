"""Validated publication-export writing."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from datp_core.domain.enums import EvidenceRole, ExperimentId, PopulationId
from datp_core.domain.values.checksums import Checksum
from datp_core.reporting.figures import FigureSpec, render_markdown_figure
from datp_core.reporting.tables import PublicationTable, render_markdown_table
from datp_core.reporting.validation import ClaimDecision, ClaimStatus
from datp_core.runtime.filesystem import write_text_atomically


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportProvenance:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    analysis_checksum: Checksum

    def __post_init__(self) -> None:
        if not isinstance(self.analysis_checksum, Checksum):
            raise TypeError("report provenance requires a typed analysis checksum")


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationBundle:
    provenance: ReportProvenance
    claims: tuple[ClaimDecision, ...]
    tables: tuple[PublicationTable, ...]
    figures: tuple[FigureSpec, ...]

    def __post_init__(self) -> None:
        if not self.claims and not self.tables and not self.figures:
            raise ValueError("publication bundles require at least one validated output")


_PUBLISHABLE_CLAIM_STATUSES = frozenset({ClaimStatus.PERMITTED, ClaimStatus.NARROWED})


def export_markdown(bundle: PublicationBundle, destination: Path) -> Path:
    blocked = tuple(decision for decision in bundle.claims if decision.status not in _PUBLISHABLE_CLAIM_STATUSES)
    permitted = tuple(decision.wording for decision in bundle.claims if decision.status in _PUBLISHABLE_CLAIM_STATUSES)
    provenance = bundle.provenance
    header = (
        "# DATP-Core Results",
        "",
        f"Experiment: `{provenance.experiment.value}`  ",
        f"Population: `{provenance.population.value}`  ",
        f"Evidence role: `{provenance.evidence_role.value}`  ",
        f"Analysis checksum: `{provenance.analysis_checksum.value}`",
        "",
    )
    blocked_section = (
        ("", "## Suppressed or blocked claims", "") + tuple(f"- {decision.reason}" for decision in blocked)
        if blocked
        else ()
    )
    table_section = tuple(chain.from_iterable(("", render_markdown_table(table)) for table in bundle.tables))
    figure_section = (
        ("", "## Figures")
        + tuple(chain.from_iterable(("", render_markdown_figure(figure)) for figure in bundle.figures))
        if bundle.figures
        else ()
    )
    sections = header + permitted + blocked_section + table_section + figure_section
    payload = "\n".join(sections).rstrip() + "\n"
    return write_text_atomically(destination, payload)
