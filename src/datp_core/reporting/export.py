"""Validated publication-export writing."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from datp_core.analysis.descriptive import DescriptiveSummary, PairedDifferenceCounts
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.multiplicity import MultiplicityResult
from datp_core.analysis.inference.wilcoxon import RankBiserialResult, WilcoxonResult
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.preparation import AnalysisDocument
from datp_core.analysis.scientific_decision import ScientificDecisionResult
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


def export_analysis_report(document: AnalysisDocument, destination: Path) -> Path:
    payload = _render_analysis_sections(document)
    return write_text_atomically(destination, payload)


def _render_analysis_sections(document: AnalysisDocument) -> str:
    sections: list[str] = []
    sections.extend(_render_decision(document.decision))
    sections.extend(_render_interval(document.interval))
    sections.extend(_render_descriptive(document.descriptive))
    sections.extend(_render_wilcoxon(document.wilcoxon))
    sections.extend(_render_rank_biserial(document.rank_biserial))
    sections.extend(_render_sign_consistency(document.sign_consistency))
    if document.multiplicity_result is not None:
        sections.extend(_render_multiplicity(document.multiplicity_result))
    if document.mechanisms:
        sections.extend(_render_mechanisms(document.mechanisms))
    return "\n".join(sections).rstrip() + "\n"


def _render_decision(decision: ScientificDecisionResult) -> list[str]:
    point = f"{decision.point_estimate.value:.6g}" if decision.point_estimate else "unavailable"
    return [
        "# Confirmatory Analysis",
        "",
        "## Decision",
        "",
        f"Evidence role: `{decision.evidence_role.value}`",
        f"Decision: `{decision.decision.value}`",
        f"Point estimate: {point}",
        f"Rationale: {decision.rationale}",
        "",
    ]


def _render_interval(interval: BootstrapInterval) -> list[str]:
    lower = f"{interval.lower_bound.value:.6g}" if interval.lower_bound else "unavailable"
    point = f"{interval.point_estimate.value:.6g}" if interval.point_estimate else "unavailable"
    upper = f"{interval.upper_bound.value:.6g}" if interval.upper_bound else "unavailable"
    lines = [
        "## BCa Bootstrap Interval",
        "",
        f"Confidence level: {interval.confidence_level.value}",
        f"Method: `{interval.method.value}`",
        f"Lower bound: {lower}",
        f"Point estimate: {point}",
        f"Upper bound: {upper}",
        f"Replicates: {interval.replicate_count.value}",
        f"Outcome: `{interval.outcome.value}`",
    ]
    if interval.reason:
        lines.append(f"Reason: {interval.reason.value}")
    return [*lines, ""]


def _render_descriptive(descriptive: DescriptiveSummary) -> list[str]:
    lines = [
        "## Descriptive Summary",
        "",
        f"Evidence role: `{descriptive.evidence_role.value}`",
        f"Values: {len(descriptive.values)} observations",
        f"Quantiles: [{descriptive.quantiles.lower.value}, {descriptive.quantiles.upper.value}]",
    ]
    if descriptive.counts:
        lines.append(
            f"Excluded: {descriptive.counts.excluded.value} | "
            f"Unavailable: {descriptive.counts.unavailable.value}"
        )
    if descriptive.statistics:
        lines.append(f"Mean: {descriptive.statistics.mean.value:.6g}")
        lines.append(f"Median: {descriptive.statistics.median.value:.6g}")
        lines.append(f"Min: {descriptive.statistics.minimum.value:.6g}")
        lines.append(f"Max: {descriptive.statistics.maximum.value:.6g}")
    if descriptive.reason:
        lines.append(f"Reason: {descriptive.reason}")
    return [*lines, ""]


def _render_wilcoxon(wilcoxon: WilcoxonResult) -> list[str]:
    lines = [
        "## Wilcoxon Signed-Rank",
        "",
        f"Availability: `{wilcoxon.availability.value}`",
        f"Nonzero pairs: {wilcoxon.nonzero_pair_count.value}",
    ]
    if wilcoxon.statistic:
        lines.append(f"Statistic: {wilcoxon.statistic.value:.6g}")
    if wilcoxon.p_value:
        lines.append(f"P-value: {wilcoxon.p_value.value:.6g}")
    if wilcoxon.computation_method:
        lines.append(f"Method: `{wilcoxon.computation_method.value}`")
    if wilcoxon.reason:
        lines.append(f"Reason: {wilcoxon.reason}")
    return [*lines, ""]


def _render_rank_biserial(rb: RankBiserialResult) -> list[str]:
    lines = [
        "## Matched-Pairs Rank-Biserial Correlation",
        "",
        f"Availability: `{rb.availability.value}`",
        f"Nonzero pairs: {rb.nonzero_pair_count.value}",
    ]
    if rb.value:
        lines.append(f"Correlation: {rb.value.value:.6g}")
    if rb.positive_rank_sum:
        lines.append(f"Positive rank sum: {rb.positive_rank_sum.value:.6g}")
    if rb.negative_rank_sum:
        lines.append(f"Negative rank sum: {rb.negative_rank_sum.value:.6g}")
    if rb.reason:
        lines.append(f"Reason: {rb.reason}")
    return [*lines, ""]


def _render_sign_consistency(sc: PairedDifferenceCounts) -> list[str]:
    total = sc.positive.value + sc.zero.value + sc.negative.value
    return [
        "## Sign Consistency",
        "",
        f"Positive: {sc.positive.value}/{total}",
        f"Zero: {sc.zero.value}/{total}",
        f"Negative: {sc.negative.value}/{total}",
        "",
    ]


def _render_multiplicity(result: MultiplicityResult) -> list[str]:
    lines = [
        "## Multiplicity Correction",
        "",
        f"Family: `{result.family_name}`",
        f"Correction: `{result.correction.value}`",
        f"Family size: {result.family_size.value}",
        "",
        "| Raw p | Adjusted p | Rejected |",
        "|---|---|---|",
    ]
    for decision in result.decisions:
        rej = "yes" if decision.rejected else "no"
        lines.append(
            f"| {decision.raw_p_value.value:.6g} | "
            f"{decision.adjusted_p_value.value:.6g} | "
            f"{rej} |"
        )
    return [*lines, ""]


def _render_mechanisms(mechanisms: tuple[MechanismEvidence, ...]) -> list[str]:
    lines = ["## Mechanism Evidence", ""]
    for idx, mechanism in enumerate(mechanisms, start=1):
        lines.append(f"{idx}. `{type(mechanism).__name__}`")
    return [*lines, ""]
