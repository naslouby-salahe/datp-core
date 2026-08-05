"""Validated publication-export writing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import EvidenceRole, ExperimentId, PopulationId
from datp_core.domain.values import Checksum
from datp_core.reporting.figures import FigureSpec
from datp_core.reporting.tables import PublicationTable, render_markdown_table
from datp_core.reporting.validation import ClaimDecision


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportProvenance:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    analysis_checksum: Checksum

    def __post_init__(self) -> None:
        if not isinstance(self.analysis_checksum, Checksum):
            object.__setattr__(self, "analysis_checksum", Checksum(self.analysis_checksum))


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationBundle:
    provenance: ReportProvenance
    claims: tuple[ClaimDecision, ...]
    tables: tuple[PublicationTable, ...]
    figures: tuple[FigureSpec, ...]

    def __post_init__(self) -> None:
        if not self.claims and not self.tables and not self.figures:
            raise ValueError("publication bundles require at least one validated output")


def export_markdown(bundle: PublicationBundle, destination: Path) -> Path:
    blocked = tuple(decision for decision in bundle.claims if decision.wording == "")
    permitted = tuple(decision.wording for decision in bundle.claims if decision.wording)
    provenance = bundle.provenance
    sections = [
        "# DATP-Core Results",
        "",
        f"Experiment: `{provenance.experiment.value}`  ",
        f"Population: `{provenance.population.value}`  ",
        f"Evidence role: `{provenance.evidence_role.value}`  ",
        f"Analysis checksum: `{provenance.analysis_checksum.value}`",
        "",
    ]
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
