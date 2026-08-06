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
from datp_core.analysis.mechanisms.absorption import AbsorptionCohortResult
from datp_core.analysis.mechanisms.association import AssociationResult
from datp_core.analysis.mechanisms.clustering import ClusterEvidenceRecord, ClusterStabilityResult
from datp_core.analysis.mechanisms.dispersion import GroupedDispersionResult
from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.analysis.mechanisms.movement import ThresholdMovement, ThresholdMovementCohort
from datp_core.analysis.preparation import AnalysisDocument, ExternalAnalysisDocument, TemporalAnalysisDocument
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, ExperimentId, MetricId, PopulationId
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.checksums import Checksum
from datp_core.reporting.figures import FigureSpec, render_markdown_figure
from datp_core.reporting.tables import PublicationTable, TableCell, render_markdown_table
from datp_core.reporting.validation import (
    ClaimDecision,
    ClaimKind,
    ClaimRequest,
    ClaimStatus,
    EvidenceDecision,
    validate_claim,
)
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


def export_confirmatory_publication(document: AnalysisDocument, output_directory: Path) -> Path:
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=document.interval.availability,
            evidence_decision=_map_decision(document.decision.decision),
            anchor_gate_passed=True,
            traffic_rate_available=False,
            wording=document.decision.rationale,
        )
    )
    tables = (
        _interval_table(document.interval),
        _wilcoxon_table(document.wilcoxon, document.rank_biserial),
        _paired_values_table(document),
    )
    bundle = PublicationBundle(
        provenance=ReportProvenance(
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            evidence_role=EvidenceRole.CONFIRMATORY,
            analysis_checksum=canonical_checksum(document),
        ),
        claims=(claim,),
        tables=tables,
        figures=(),
    )
    export_analysis_report(document, output_directory / "analysis_report.md")
    return export_markdown(bundle, output_directory / "publication.md")


def export_external_publication(document: ExternalAnalysisDocument, output_directory: Path) -> Path:
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.EXTERNAL,
            evidence_role=document.plan.evidence_role,
            metric=document.plan.metric,
            availability=document.interval.availability,
            evidence_decision=EvidenceDecision.BOUNDARY,
            anchor_gate_passed=True,
            traffic_rate_available=False,
            wording="External paired threshold contrast remains supplementary and claim-bounded.",
        )
    )
    payload = "\n".join(
        [
            *_render_interval(document.interval),
            *_render_descriptive(document.descriptive),
            *_render_wilcoxon(document.wilcoxon),
            *_render_rank_biserial(document.rank_biserial),
            *_render_sign_consistency(document.sign_consistency),
            *_render_paired_contrasts(document.contrasts),
            *_render_mechanisms(document.mechanisms),
            f"Unavailable reason: {document.unavailable_reason or 'none'}",
            "",
        ]
    )
    write_text_atomically(output_directory / "external_analysis_report.md", payload)
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION
                if document.plan.evidence_role is EvidenceRole.EXTERNAL_VALIDATION
                else ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
                population=document.plan.population,
                evidence_role=document.plan.evidence_role,
                analysis_checksum=canonical_checksum(document),
            ),
            claims=(claim,),
            tables=(_interval_table(document.interval),),
            figures=(),
        ),
        output_directory / "publication.md",
    )


def export_temporal_publication(document: TemporalAnalysisDocument, output_directory: Path) -> Path:
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.TEMPORAL,
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=AvailabilityStatus.AVAILABLE,
            evidence_decision=_map_decision(document.campaign_decision.decision),
            anchor_gate_passed=True,
            traffic_rate_available=False,
            wording=document.campaign_decision.rationale,
        )
    )
    lines = [
        "# Temporal Campaign Analysis",
        "",
        f"Experiment: `{document.experiment.value}`",
        f"Threshold method: `{document.threshold_method.value}`",
        f"Campaign decision: `{document.campaign_decision.decision.value}`",
        f"Rationale: {document.campaign_decision.rationale}",
        f"Paired seeds: {', '.join(str(seed.value) for seed in document.paired_seed_identities)}",
        "",
        "## Seed recoveries",
        "",
        "| Seed | Static CV | Frozen CV | Recalibrated CV | Drift excess | Recovered | Ratio | Interpretation |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in document.records:
        recovery = record.recovery
        ratio = "undefined" if recovery.recovery_ratio is None else f"{recovery.recovery_ratio.value:.6g}"
        lines.append(
            f"| {recovery.seed.value} | {recovery.static_reference_cv.value:.6g} | "
            f"{recovery.frozen_future_cv.value:.6g} | {recovery.recalibrated_future_cv.value:.6g} | "
            f"{recovery.drift_excess.value:.6g} | {recovery.recovered_amount.value:.6g} | "
            f"{ratio} | `{record.interpretation.value}` |"
        )
    lines.extend(
        [
            "",
            f"Detector checksum: `{document.frozen_provenance.checkpoint_checksum.value}`",
            f"Preprocessing checksum: `{document.frozen_provenance.preprocessing_state_set_checksum.value}`",
            f"Coordinate checksum: `{document.frozen_provenance.coordinate_checksum.value}`",
            "",
        ]
    )
    write_text_atomically(output_directory / "temporal_analysis_report.md", "\n".join(lines))
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=document.experiment,
                population=PopulationId.EDGE_TEMPORAL_GROUPS,
                evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
                analysis_checksum=canonical_checksum(document),
            ),
            claims=(claim,),
            tables=(
                PublicationTable(
                    title="Temporal campaign decision",
                    cells=(
                        TableCell(
                            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                            availability=AvailabilityStatus.AVAILABLE,
                            rendered_value=document.campaign_decision.decision.value,
                            evidence=document.campaign_decision.rationale,
                        ),
                    ),
                ),
            ),
            figures=(),
        ),
        output_directory / "publication.md",
    )


def export_mechanism_publication(
    mechanisms: tuple[MechanismEvidence, ...],
    *,
    experiment: ExperimentId,
    population: PopulationId,
    output_directory: Path,
) -> Path:
    payload = "\n".join(_render_mechanisms(mechanisms))
    write_text_atomically(output_directory / "mechanism_report.md", payload)
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=experiment,
                population=population,
                evidence_role=EvidenceRole.MECHANISM,
                analysis_checksum=canonical_checksum(mechanisms),
            ),
            claims=(
                ClaimDecision(
                    status=ClaimStatus.NARROWED,
                    wording="Mechanism evidence is associative and non-confirmatory.",
                    reason="mechanism claim tier",
                ),
            ),
            tables=(
                PublicationTable(
                    title="Mechanism inventory",
                    cells=(
                        TableCell(
                            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                            availability=AvailabilityStatus.AVAILABLE,
                            rendered_value=str(len(mechanisms)),
                            evidence="count of typed mechanism records",
                        ),
                    ),
                ),
            ),
            figures=(),
        ),
        output_directory / "publication.md",
    )


def _render_analysis_sections(document: AnalysisDocument) -> str:
    sections: list[str] = []
    sections.extend(_render_decision(document.decision))
    sections.extend(_render_interval(document.interval))
    sections.extend(_render_descriptive(document.descriptive))
    sections.extend(_render_wilcoxon(document.wilcoxon))
    sections.extend(_render_rank_biserial(document.rank_biserial))
    sections.extend(_render_sign_consistency(document.sign_consistency))
    sections.extend(_render_paired_contrasts(document.contrasts))
    if document.multiplicity_result is not None:
        sections.extend(_render_multiplicity(document.multiplicity_result))
    if document.mechanisms:
        sections.extend(_render_mechanisms(document.mechanisms))
    if document.unavailable_reason:
        sections.extend(["## Unavailable / blocked", "", document.unavailable_reason, ""])
    if document.excluded_seeds:
        seeds = ", ".join(str(seed.value) for seed in document.excluded_seeds)
        sections.extend(["## Exclusions", "", f"Excluded seeds: {seeds}", ""])
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
    if interval.adjustment is not None:
        lines.append(f"Bias correction: {interval.adjustment.bias_correction.value:.6g}")
        lines.append(f"Acceleration: {interval.adjustment.acceleration.value:.6g}")
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
            f"Excluded: {descriptive.counts.excluded.value} | Unavailable: {descriptive.counts.unavailable.value}"
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
    if wilcoxon.fallback_reason:
        lines.append(f"Fallback reason: {wilcoxon.fallback_reason}")
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


def _render_paired_contrasts(contrasts: tuple) -> list[str]:
    lines = [
        "## Paired Seed Values",
        "",
        "| Seed | Shared | Local | Delta | Model checksum | Checkpoint |",
        "|---|---:|---:|---:|---|---|",
    ]
    for contrast in contrasts:
        lines.append(
            f"| {contrast.seed.value} | {contrast.left_value.value:.6g} | "
            f"{contrast.right_value.value:.6g} | {contrast.delta.value:.6g} | "
            f"`{contrast.fixed_score.model_checksum.value[:12]}` | "
            f"`{contrast.fixed_score.selected_checkpoint_checksum.value[:12]}` |"
        )
    return [*lines, ""]


def _render_multiplicity(result: MultiplicityResult) -> list[str]:
    lines = [
        "## Multiplicity Correction",
        "",
        f"Family: `{result.family_name}`",
        f"Correction: `{result.correction.value}`",
        f"Family size: {result.family_size.value}",
        "",
        "| Hypothesis | Experiment | Metric | Comparison | Raw p | Adjusted p | Rejected |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for decision in result.decisions:
        hypothesis = decision.hypothesis
        rej = "yes" if decision.rejected else "no"
        lines.append(
            f"| `{hypothesis.hypothesis_id}` | `{hypothesis.experiment.value}` | "
            f"`{hypothesis.metric.value}` | {hypothesis.comparison} | "
            f"{decision.raw_p_value.value:.6g} | {decision.adjusted_p_value.value:.6g} | {rej} |"
        )
    return [*lines, ""]


def _render_mechanisms(mechanisms: tuple[MechanismEvidence, ...]) -> list[str]:
    lines = ["## Mechanism Evidence", ""]
    for index, mechanism in enumerate(mechanisms, start=1):
        lines.append(f"### Mechanism {index}: `{type(mechanism).__name__}`")
        lines.extend(_render_one_mechanism(mechanism))
        lines.append("")
    return lines


def _render_one_mechanism(mechanism: MechanismEvidence) -> list[str]:
    match mechanism:
        case AssociationResult():
            lines = [
                f"Observations: {mechanism.observation_count.value}",
                f"Availability: `{mechanism.availability.value}`",
            ]
            if mechanism.statistics is not None:
                stats = mechanism.statistics
                lines.extend(
                    [
                        f"Spearman rho: {stats.spearman_rho.value:.6g}",
                        f"Spearman p: {stats.spearman_p_value.value:.6g}",
                        f"Slope: {stats.regression_slope.value:.6g} "
                        f"(SE {stats.regression_slope_standard_error.value:.6g})",
                        f"R²: {stats.r_squared.value:.6g}",
                        f"Evidentiary sufficient: {stats.evidentiary_sufficient}",
                    ]
                )
            if mechanism.reason:
                lines.append(f"Reason: {mechanism.reason}")
            return lines
        case DivergenceResult():
            lines = [
                f"Clients: {len(mechanism.clients)}",
                f"Availability: `{mechanism.availability.value}`",
                f"Protocol bin count: {mechanism.protocol.bin_count.value}",
            ]
            if mechanism.aggregate is not None:
                lines.append(f"Aggregate JS: {mechanism.aggregate.value:.6g}")
                lines.append(
                    f"Pairwise values: {', '.join(f'{value.value:.6g}' for value in mechanism.pairwise_values)}"
                )
            if mechanism.reason:
                lines.append(f"Reason: {mechanism.reason}")
            return lines
        case ClusterStabilityResult():
            return [
                f"ARI: {mechanism.adjusted_rand_index.value:.6g}",
                f"Clients: {len(mechanism.compared_clients)}",
                f"Left singletons: {len(mechanism.left_partition.singleton_groups)}",
                f"Right empty groups: {len(mechanism.right_partition.empty_groups)}",
            ]
        case ClusterEvidenceRecord():
            recovery = (
                f"{mechanism.recovery_fraction.value:.6g}"
                if mechanism.recovery_fraction is not None
                else mechanism.recovery_fraction_reason
            )
            return [
                f"Seed: {mechanism.seed.value}",
                f"Memberships: {len(mechanism.memberships)}",
                f"Contributing quantile dispersion: {mechanism.contributing_quantile_dispersion.value:.6g}",
                f"Effective threshold dispersion: {mechanism.effective_threshold_dispersion.value:.6g}",
                f"Recovery fraction: {recovery}",
                f"Empty clusters: {len(mechanism.partition.empty_groups)}",
            ]
        case GroupedDispersionResult():
            return [
                f"Availability: `{mechanism.availability.value}`",
                f"Groups: {len(mechanism.group_sizes)}",
                f"Singletons: {len(mechanism.singleton_groups)}",
                f"Empty: {len(mechanism.empty_groups)}",
                (
                    f"Across-group threshold spread: {mechanism.across_group_threshold_spread.value:.6g}"
                    if mechanism.across_group_threshold_spread is not None
                    else f"Reason: {mechanism.reason}"
                ),
            ]
        case ThresholdMovement():
            delta_tpr = f"{mechanism.delta_tpr.value:.6g}" if mechanism.delta_tpr is not None else "unavailable"
            return [
                f"Client: `{mechanism.client.client_id}`",
                f"Seed: {mechanism.seed.value}",
                f"Δ threshold: {mechanism.delta_threshold.value:.6g}",
                f"Δ FPR: {mechanism.delta_fpr.value:.6g}",
                f"Δ TPR: {delta_tpr}",
            ]
        case ThresholdMovementCohort():
            return [
                f"Movements: {len(mechanism.movements)}",
                f"Availability: `{mechanism.availability.value}`",
                (
                    f"Mean Δ FPR: {mechanism.mean_delta_fpr.value:.6g}"
                    if mechanism.mean_delta_fpr is not None
                    else f"Reason: {mechanism.reason}"
                ),
            ]
        case AbsorptionCohortResult():
            return [
                f"Seeds: {len(mechanism.observations)}",
                f"Decision: `{mechanism.decision.decision.value}`",
                f"Rationale: {mechanism.decision.rationale}",
                (
                    f"Mean retention: {mechanism.mean_retention.value:.6g}"
                    if mechanism.mean_retention is not None
                    else "Mean retention: unavailable"
                ),
            ]
        case ScientificDecisionResult():
            return [
                f"Decision: `{mechanism.decision.value}`",
                f"Evidence role: `{mechanism.evidence_role.value}`",
                f"Rationale: {mechanism.rationale}",
            ]
        case _:
            return [f"Unhandled mechanism type: {type(mechanism).__name__}"]


def _interval_table(interval: BootstrapInterval) -> PublicationTable:
    point = f"{interval.point_estimate.value:.6g}" if interval.point_estimate else ""
    return PublicationTable(
        title="Paired BCa interval",
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=interval.availability,
                rendered_value=point,
                evidence=f"BCa outcome={interval.outcome.value}",
            ),
        ),
    )


def _wilcoxon_table(wilcoxon: WilcoxonResult, rank_biserial: RankBiserialResult) -> PublicationTable:
    p_value = f"{wilcoxon.p_value.value:.6g}" if wilcoxon.p_value else ""
    effect = f"{rank_biserial.value.value:.6g}" if rank_biserial.value else ""
    return PublicationTable(
        title="Secondary paired inference",
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=wilcoxon.availability,
                rendered_value=p_value,
                evidence=(
                    f"Wilcoxon method={wilcoxon.computation_method.value if wilcoxon.computation_method else 'none'}"
                ),
            ),
            TableCell(
                metric=MetricId.MEAN_FPR,
                availability=rank_biserial.availability,
                rendered_value=effect,
                evidence="matched-pairs rank-biserial",
            ),
        ),
    )


def _paired_values_table(document: AnalysisDocument) -> PublicationTable:
    if not document.contrasts:
        return PublicationTable(
            title="Paired seed inventory",
            cells=(
                TableCell(
                    metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                    availability=AvailabilityStatus.UNAVAILABLE,
                    rendered_value="",
                    evidence=document.unavailable_reason or "no paired contrasts",
                ),
            ),
        )
    mean_delta = sum(item.delta.value for item in document.contrasts) / len(document.contrasts)
    return PublicationTable(
        title="Paired seed inventory",
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value=f"{mean_delta:.6g}",
                evidence=f"{len(document.contrasts)} paired seeds with fixed-score provenance",
            ),
        ),
    )


def _map_decision(decision: ScientificDecision) -> EvidenceDecision:
    match decision:
        case ScientificDecision.SUPPORTED:
            return EvidenceDecision.SUPPORTED
        case ScientificDecision.DIRECTIONAL_INCONCLUSIVE:
            return EvidenceDecision.DIRECTIONAL_INCONCLUSIVE
        case ScientificDecision.OPPOSITE_DIRECTION:
            return EvidenceDecision.REVERSED
        case ScientificDecision.NO_OBSERVED_ADVANTAGE:
            return EvidenceDecision.NULL
        case ScientificDecision.BOUNDARY_RESULT:
            return EvidenceDecision.BOUNDARY
        case _:
            return EvidenceDecision.UNSTABLE
