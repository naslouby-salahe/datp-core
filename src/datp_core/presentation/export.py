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
from datp_core.analysis.mechanisms.movement import (
    ThresholdMovement,
    ThresholdMovementCohort,
    ThresholdMovementMultiSeedUncertainty,
)
from datp_core.analysis.preparation import AnalysisDocument, ExternalAnalysisDocument, TemporalAnalysisDocument
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.identifiers import (
    AvailabilityStatus,
    ClaimWording,
    EvidenceRole,
    ExperimentId,
    FileContentText,
    MetricId,
    PopulationId,
    ReportLine,
)
from datp_core.core.numeric import MetricValue
from datp_core.experiments.anchor.contracts import VerifiedAnchorGateArtifact
from datp_core.presentation.figures import FigureSpec, render_markdown_figure
from datp_core.presentation.tables import (
    EvidenceText,
    PublicationTable,
    TableCell,
    TableCellRenderedValue,
    TableTitle,
    render_markdown_table,
)
from datp_core.presentation.validation import (
    ClaimDecision,
    ClaimKind,
    ClaimReason,
    ClaimRequest,
    ClaimStatus,
    EvidenceDecision,
    validate_claim,
)
from datp_core.runtime.filesystem import write_text_atomically

PUBLICATION_FILENAME = "publication.md"
MECHANISM_REPORT_FILENAME = "mechanism_report.md"


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
    permitted = tuple(
        decision.wording
        for decision in bundle.claims
        if decision.status in _PUBLISHABLE_CLAIM_STATUSES and decision.wording is not None
    )
    evidence_publishable = bool(permitted) or not bundle.claims
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
    table_section = (
        tuple(chain.from_iterable(("", render_markdown_table(table)) for table in bundle.tables))
        if evidence_publishable
        else ()
    )
    figure_section = (
        ("", "## Figures")
        + tuple(chain.from_iterable(("", render_markdown_figure(figure)) for figure in bundle.figures))
        if evidence_publishable and bundle.figures
        else ()
    )
    sections = header + permitted + blocked_section + table_section + figure_section
    payload = "\n".join(sections).rstrip() + "\n"
    return write_text_atomically(destination, FileContentText(payload))


def export_analysis_report(document: AnalysisDocument, destination: Path) -> Path:
    payload = _render_analysis_sections(document)
    return write_text_atomically(destination, FileContentText(payload))


def export_confirmatory_publication(
    document: AnalysisDocument,
    output_directory: Path,
    *,
    verified_anchor_gate: VerifiedAnchorGateArtifact | None,
    figures: tuple[FigureSpec, ...] = (),
) -> Path:
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.CONFIRMATORY,
            evidence_role=EvidenceRole.CONFIRMATORY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=document.interval.availability,
            evidence_decision=_map_decision(document.decision.decision),
            verified_anchor_gate=verified_anchor_gate,
            traffic_rate_available=False,
            wording=ClaimWording(document.decision.rationale),
        )
    )
    tables = (
        _interval_table(document.interval),
        _wilcoxon_table(document.wilcoxon, document.rank_biserial),
        _paired_values_table(document),
        *_mechanism_tables(document.mechanisms),
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
        figures=figures,
    )
    export_analysis_report(document, output_directory / "analysis_report.md")
    return export_markdown(bundle, output_directory / PUBLICATION_FILENAME)


def export_external_publication(document: ExternalAnalysisDocument, output_directory: Path) -> Path:
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.EXTERNAL,
            evidence_role=document.plan.evidence_role,
            metric=document.plan.metric,
            availability=document.interval.availability,
            evidence_decision=EvidenceDecision.BOUNDARY,
            verified_anchor_gate=None,
            traffic_rate_available=False,
            wording=ClaimWording("External paired threshold contrast remains supplementary and claim-bounded."),
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
    write_text_atomically(output_directory / "external_analysis_report.md", FileContentText(payload))
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
        output_directory / PUBLICATION_FILENAME,
    )


def export_temporal_publication(document: TemporalAnalysisDocument, output_directory: Path) -> Path:
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.TEMPORAL,
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            availability=document.campaign_decision.availability,
            evidence_decision=_map_decision(document.campaign_decision.decision),
            verified_anchor_gate=None,
            traffic_rate_available=False,
            wording=ClaimWording(document.campaign_decision.rationale),
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
        (
            "| Seed | Static CV | Frozen CV | Recalibrated CV | Mean FPR static | "
            "Mean FPR frozen | Mean FPR recal | Drift excess | Recovered | Ratio | Interpretation |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in document.records:
        recovery = record.recovery
        ratio = "undefined" if recovery.recovery_ratio is None else f"{recovery.recovery_ratio.value:.6g}"
        mean_static = "—" if recovery.mean_fpr_static is None else f"{recovery.mean_fpr_static.value:.6g}"
        mean_frozen = "—" if recovery.mean_fpr_frozen is None else f"{recovery.mean_fpr_frozen.value:.6g}"
        mean_recal = "—" if recovery.mean_fpr_recalibrated is None else f"{recovery.mean_fpr_recalibrated.value:.6g}"
        lines.append(
            f"| {recovery.seed.value} | {recovery.static_reference_cv.value:.6g} | "
            f"{recovery.frozen_future_cv.value:.6g} | {recovery.recalibrated_future_cv.value:.6g} | "
            f"{mean_static} | {mean_frozen} | {mean_recal} | "
            f"{recovery.drift_excess.value:.6g} | {recovery.recovered_amount.value:.6g} | "
            f"{ratio} | `{record.interpretation.value}` |"
        )
    lines.extend(["", "## Per-seed provenance", ""])
    for record in document.records:
        recovery = record.recovery
        provenance = recovery.provenance
        if provenance is None:
            raise ValueError(
                f"temporal publication requires provenance for seed {recovery.seed.value}; "
                "missing provenance cannot be exported"
            )
        lines.append(
            f"- seed `{recovery.seed.value}`: checkpoint=`{provenance.frozen_future.checkpoint_checksum.value}` "
            f"preprocess=`{provenance.frozen_future.preprocessing_state_set_checksum.value}` "
            f"split=`{provenance.frozen_future.split_manifest_checksum.value}` "
            f"eval_scores=`{provenance.frozen_future.evaluation_score_set_checksum.value}` "
            f"static_threshold=`{provenance.static_threshold_checksum.value}` "
            f"frozen_threshold=`{provenance.frozen_threshold_checksum.value}` "
            f"recalibrated_threshold=`{provenance.recalibrated_threshold_checksum.value}` "
            f"static_evaluation=`{provenance.static_evaluation_checksum.value}` "
            f"frozen_evaluation=`{provenance.frozen_evaluation_checksum.value}` "
            f"recalibrated_evaluation=`{provenance.recalibrated_evaluation_checksum.value}`"
        )
        for trajectory in recovery.client_trajectories:
            lines.append(
                f"  - client `{trajectory.client_id.value}` eligible={trajectory.eligible} "
                f"fpr_static={_optional_metric(trajectory.fpr_static)} "
                f"fpr_frozen={_optional_metric(trajectory.fpr_frozen)} "
                f"fpr_recal={_optional_metric(trajectory.fpr_recalibrated)}"
            )
    lines.append("")
    write_text_atomically(output_directory / "temporal_analysis_report.md", FileContentText("\n".join(lines)))
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
                    title=TableTitle("Temporal campaign decision"),
                    cells=(
                        TableCell(
                            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                            availability=(
                                AvailabilityStatus.UNAVAILABLE
                                if document.campaign_decision.decision is ScientificDecision.BLOCKED
                                else AvailabilityStatus.AVAILABLE
                            ),
                            rendered_value=TableCellRenderedValue(document.campaign_decision.decision.value),
                            evidence=EvidenceText(document.campaign_decision.rationale),
                        ),
                    ),
                ),
            ),
            figures=(),
        ),
        output_directory / PUBLICATION_FILENAME,
    )


def export_mechanism_publication(
    mechanisms: tuple[MechanismEvidence, ...],
    *,
    experiment: ExperimentId,
    population: PopulationId,
    output_directory: Path,
    evidence_role: EvidenceRole,
    figures: tuple[FigureSpec, ...] = (),
) -> Path:
    payload = "\n".join(_render_mechanisms(mechanisms))
    write_text_atomically(output_directory / MECHANISM_REPORT_FILENAME, FileContentText(payload))
    tables = _mechanism_tables(mechanisms)
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=experiment,
                population=population,
                evidence_role=evidence_role,
                analysis_checksum=canonical_checksum(mechanisms),
            ),
            claims=(
                ClaimDecision(
                    status=ClaimStatus.NARROWED,
                    wording=ClaimWording("Mechanism evidence is associative and non-confirmatory."),
                    reason=ClaimReason("mechanism claim tier"),
                ),
            ),
            tables=tables
            if tables
            else (
                PublicationTable(
                    title=TableTitle("Mechanism evidence"),
                    cells=(
                        TableCell(
                            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                            availability=AvailabilityStatus.UNAVAILABLE,
                            rendered_value=TableCellRenderedValue(""),
                            evidence=EvidenceText("no mechanism evidence values were available for tabular export"),
                        ),
                    ),
                ),
            ),
            figures=figures,
        ),
        output_directory / PUBLICATION_FILENAME,
    )


def _render_analysis_sections(
    document: AnalysisDocument,
) -> ReportLine:
    sections: list[ReportLine] = []
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
        sections.extend(
            [
                ReportLine("## Unavailable / blocked"),
                ReportLine(""),
                ReportLine(document.unavailable_reason),
                ReportLine(""),
            ]
        )
    if document.excluded_seeds:
        seeds = ", ".join(str(seed.value) for seed in document.excluded_seeds)
        sections.extend(
            [ReportLine("## Exclusions"), ReportLine(""), ReportLine(f"Excluded seeds: {seeds}"), ReportLine("")]
        )
    return ReportLine("\n".join(sections).rstrip() + "\n")


def _render_decision(
    decision: ScientificDecisionResult,
) -> list[ReportLine]:
    point = f"{decision.point_estimate.value:.6g}" if decision.point_estimate else "unavailable"
    return [
        ReportLine(line)
        for line in [
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
    ]


def _render_interval(
    interval: BootstrapInterval,
) -> list[ReportLine]:
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
    return [ReportLine(line) for line in [*lines, ""]]


def _render_descriptive(
    descriptive: DescriptiveSummary,
) -> list[ReportLine]:
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
    return [ReportLine(line) for line in [*lines, ""]]


def _render_wilcoxon(
    wilcoxon: WilcoxonResult,
) -> list[ReportLine]:
    lines = [
        "## Wilcoxon Signed-Rank",
        "",
        f"Availability: `{wilcoxon.availability.value}`",
        f"Nonzero pairs: {wilcoxon.nonzero_pair_count.value}",
        f"Effective sample size: {wilcoxon.effective_sample_size.value}",
    ]
    if wilcoxon.requested_method is not None:
        lines.append(f"Requested method: `{wilcoxon.requested_method.value}`")
    if wilcoxon.zero_method is not None:
        lines.append(f"Zero handling: `{wilcoxon.zero_method.value}`")
    if wilcoxon.statistic:
        lines.append(f"Statistic: {wilcoxon.statistic.value:.6g}")
    if wilcoxon.p_value:
        lines.append(f"P-value: {wilcoxon.p_value.value:.6g}")
    if wilcoxon.computation_method:
        lines.append(f"Executed method: `{wilcoxon.computation_method.value}`")
    if wilcoxon.fallback_reason:
        lines.append(f"Fallback reason: {wilcoxon.fallback_reason}")
    if wilcoxon.reason:
        lines.append(f"Reason: {wilcoxon.reason}")
    return [ReportLine(line) for line in [*lines, ""]]


def _render_rank_biserial(
    rb: RankBiserialResult,
) -> list[ReportLine]:
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
    return [ReportLine(line) for line in [*lines, ""]]


def _render_sign_consistency(
    sc: PairedDifferenceCounts,
) -> list[ReportLine]:
    total = sc.positive.value + sc.zero.value + sc.negative.value
    return [
        ReportLine(line)
        for line in [
            "## Sign Consistency",
            "",
            f"Positive: {sc.positive.value}/{total}",
            f"Zero: {sc.zero.value}/{total}",
            f"Negative: {sc.negative.value}/{total}",
            "",
        ]
    ]


def _render_paired_contrasts(
    contrasts: tuple,
) -> list[ReportLine]:
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
    return [ReportLine(line) for line in [*lines, ""]]


def _render_multiplicity(
    result: MultiplicityResult,
) -> list[ReportLine]:
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
    return [ReportLine(line) for line in [*lines, ""]]


def _render_mechanisms(
    mechanisms: tuple[MechanismEvidence, ...],
) -> list[ReportLine]:
    lines = ["## Mechanism Evidence", ""]
    for index, mechanism in enumerate(mechanisms, start=1):
        lines.append(f"### Mechanism record {index}: {_mechanism_title(mechanism)}")
        lines.extend(_render_one_mechanism(mechanism))
        lines.append("")
    return [ReportLine(line) for line in lines]


def _mechanism_title(
    mechanism: MechanismEvidence,
) -> ReportLine:
    match mechanism:
        case AssociationResult():
            return ReportLine("heterogeneity_benefit_association")
        case DivergenceResult():
            return ReportLine("jensen_shannon_score_divergence")
        case ClusterStabilityResult():
            return ReportLine("cluster_stability")
        case ClusterEvidenceRecord():
            return ReportLine("cluster_evidence")
        case GroupedDispersionResult():
            return ReportLine("grouped_dispersion")
        case ThresholdMovement():
            return ReportLine("threshold_movement")
        case ThresholdMovementCohort():
            return ReportLine("threshold_movement_cohort")
        case ThresholdMovementMultiSeedUncertainty():
            return ReportLine("threshold_movement_across_seed_uncertainty")
        case AbsorptionCohortResult():
            return ReportLine("model_personalization_absorption")
        case ScientificDecisionResult():
            return ReportLine("scientific_decision")
        case _:
            return ReportLine("mechanism_evidence")


def _mechanism_tables(mechanisms: tuple[MechanismEvidence, ...]) -> tuple[PublicationTable, ...]:
    cells: list[TableCell] = []
    for mechanism in mechanisms:
        match mechanism:
            case AssociationResult() if mechanism.statistics is not None:
                stats = mechanism.statistics
                cells.append(
                    TableCell(
                        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(f"{stats.spearman_rho.value:.6g}"),
                        evidence=EvidenceText(
                            f"Spearman association n={mechanism.observation_count.value}; "
                            f"slope={stats.regression_slope.value:.6g}; R²={stats.r_squared.value:.6g}; "
                            f"sufficient={stats.evidentiary_sufficient}"
                        ),
                    )
                )
            case DivergenceResult() if mechanism.aggregate is not None:
                cells.append(
                    TableCell(
                        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(f"{mechanism.aggregate.value:.6g}"),
                        evidence=EvidenceText(
                            f"mean pairwise JS distance (base-2), clients={len(mechanism.clients)}, "
                            f"bins={mechanism.protocol.bin_count.value}"
                        ),
                    )
                )
            case ThresholdMovementCohort() if mechanism.mean_delta_fpr is not None:
                dispersion = (
                    f"{mechanism.client_dispersion_delta_fpr.value:.6g}"
                    if mechanism.client_dispersion_delta_fpr is not None
                    else "unavailable"
                )
                cells.append(
                    TableCell(
                        metric=MetricId.MEAN_FPR,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(f"{mechanism.mean_delta_fpr.value:.6g}"),
                        evidence=EvidenceText(
                            f"mean ΔFPR; client_dispersion={dispersion}; n={len(mechanism.movements)}"
                        ),
                    )
                )
            case AbsorptionCohortResult() if mechanism.mean_retention is not None:
                cells.append(
                    TableCell(
                        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                        availability=AvailabilityStatus.AVAILABLE,
                        rendered_value=TableCellRenderedValue(f"{mechanism.mean_retention.value:.6g}"),
                        evidence=EvidenceText(
                            f"mean CV(FPR) retention; decision={mechanism.decision.decision.value}; "
                            f"seeds={len(mechanism.observations)}; "
                            f"alternative_route_seeds={mechanism.alternative_route_seed_count}"
                        ),
                    )
                )
            case ClusterEvidenceRecord() if mechanism.cv_fpr_equity_recovery_fraction is not None:
                cells.append(
                    TableCell(
                        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(f"{mechanism.cv_fpr_equity_recovery_fraction.value:.6g}"),
                        evidence=EvidenceText(
                            f"CV(FPR) equity recovery; empty_clusters={len(mechanism.partition.empty_groups)}; "
                            f"seed={mechanism.seed.value}"
                        ),
                    )
                )
            case _:
                continue
    tables: list[PublicationTable] = []
    if cells:
        tables.append(PublicationTable(title=TableTitle("Mechanism scientific values"), cells=tuple(cells)))
    return tuple(tables)


def _render_one_mechanism(
    mechanism: MechanismEvidence,
) -> list[ReportLine]:
    match mechanism:
        case AssociationResult():
            return _render_association_result(mechanism)
        case DivergenceResult():
            return _render_divergence_result(mechanism)
        case ClusterStabilityResult():
            return _render_cluster_stability_result(mechanism)
        case ClusterEvidenceRecord():
            return _render_cluster_evidence_record(mechanism)
        case GroupedDispersionResult():
            return _render_grouped_dispersion_result(mechanism)
        case ThresholdMovement():
            return _render_threshold_movement(mechanism)
        case ThresholdMovementCohort():
            return _render_threshold_movement_cohort(mechanism)
        case ThresholdMovementMultiSeedUncertainty():
            return _render_threshold_movement_uncertainty(mechanism)
        case AbsorptionCohortResult():
            return _render_absorption_cohort_result(mechanism)
        case ScientificDecisionResult():
            return _render_scientific_decision_result(mechanism)
        case _:
            return [ReportLine("Unhandled mechanism evidence kind")]


def _render_association_result(mechanism: AssociationResult) -> list[ReportLine]:
    lines = [
        f"Observations: {mechanism.observation_count.value}",
        f"Availability: `{mechanism.availability.value}`",
    ]
    if mechanism.statistics is not None:
        stats = mechanism.statistics
        lower, upper = stats.regression_slope_confidence_interval
        lines.extend(
            [
                f"Spearman rho: {stats.spearman_rho.value:.6g}",
                f"Spearman p: {stats.spearman_p_value.value:.6g}",
                f"Intercept: {stats.regression_intercept.value:.6g}",
                f"Slope: {stats.regression_slope.value:.6g} (SE {stats.regression_slope_standard_error.value:.6g})",
                f"Slope CI: [{lower.value:.6g}, {upper.value:.6g}]",
                f"R²: {stats.r_squared.value:.6g}",
                f"Leverage: {', '.join(f'{value.value:.6g}' for value in stats.leverage)}",
                f"Influence: {', '.join(f'{value.value:.6g}' for value in stats.influence)}",
                f"Evidentiary sufficient: {stats.evidentiary_sufficient}",
            ]
        )
    if mechanism.reason:
        lines.append(f"Reason: {mechanism.reason}")
    return [ReportLine(line) for line in lines]


def _render_divergence_result(mechanism: DivergenceResult) -> list[ReportLine]:
    lines = [
        f"Clients: {len(mechanism.clients)}",
        f"Availability: `{mechanism.availability.value}`",
        f"Score source: `{mechanism.protocol.score_source.value}`",
        f"Shared support: `{mechanism.protocol.shared_support.value}`",
        f"Binning: `{mechanism.protocol.binning.value}` bins={mechanism.protocol.bin_count.value}",
        f"Smoothing: {mechanism.protocol.smoothing_constant.value:.6g}",
        f"Log base: `{mechanism.protocol.logarithm_base.value}`",
        f"Aggregation: `{mechanism.protocol.aggregation.value}`",
    ]
    if mechanism.source_score_checksum is not None:
        lines.append(f"Source score checksum: `{mechanism.source_score_checksum.value}`")
    if mechanism.aggregate is not None:
        lines.append(f"Aggregate JS distance: {mechanism.aggregate.value:.6g}")
        lines.append(f"Pairwise values: {', '.join(f'{value.value:.6g}' for value in mechanism.pairwise_values)}")
    if mechanism.reason:
        lines.append(f"Reason: {mechanism.reason}")
    return [ReportLine(line) for line in lines]


def _render_cluster_stability_result(mechanism: ClusterStabilityResult) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
            f"ARI: {mechanism.adjusted_rand_index.value:.6g}",
            f"Clients: {len(mechanism.compared_clients)}",
            f"Left singletons: {len(mechanism.left_partition.singleton_groups)}",
            f"Right empty groups: {len(mechanism.right_partition.empty_groups)}",
        ]
    ]


def _render_cluster_evidence_record(mechanism: ClusterEvidenceRecord) -> list[ReportLine]:
    equity = (
        f"{mechanism.cv_fpr_equity_recovery_fraction.value:.6g}"
        if mechanism.cv_fpr_equity_recovery_fraction is not None
        else mechanism.cv_fpr_equity_recovery_reason
    )
    threshold_recovery = (
        f"{mechanism.threshold_dispersion_recovery_fraction.value:.6g}"
        if mechanism.threshold_dispersion_recovery_fraction is not None
        else mechanism.threshold_dispersion_recovery_reason
    )
    contributing = (
        f"{mechanism.contributing_quantile_dispersion.value:.6g}"
        if mechanism.contributing_quantile_dispersion is not None
        else (mechanism.dispersion_unavailable_reason or "unavailable")
    )
    effective = (
        f"{mechanism.effective_threshold_dispersion.value:.6g}"
        if mechanism.effective_threshold_dispersion is not None
        else (mechanism.dispersion_unavailable_reason or "unavailable")
    )
    return [
        ReportLine(line)
        for line in [
            f"Seed: {mechanism.seed.value}",
            f"Memberships: {len(mechanism.memberships)}",
            f"Contributing quantile dispersion: {contributing}",
            f"Effective threshold dispersion: {effective}",
            f"CV(FPR) equity recovery: {equity}",
            f"Threshold-dispersion recovery: {threshold_recovery}",
            f"Empty clusters: {len(mechanism.partition.empty_groups)}",
            f"Evidence availability: `{mechanism.evidence_availability.value}`",
        ]
    ]


def _render_grouped_dispersion_result(mechanism: GroupedDispersionResult) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
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
    ]


def _render_threshold_movement(mechanism: ThresholdMovement) -> list[ReportLine]:
    delta_tpr = f"{mechanism.delta_tpr.value:.6g}" if mechanism.delta_tpr is not None else "unavailable"
    return [
        ReportLine(line)
        for line in [
            f"Client: `{mechanism.client.client_id.value}`",
            f"Seed: {mechanism.seed.value}",
            f"Δ threshold: {mechanism.delta_threshold.value:.6g}",
            f"Δ FPR: {mechanism.delta_fpr.value:.6g}",
            f"Δ TPR: {delta_tpr}",
        ]
    ]


def _render_threshold_movement_cohort(mechanism: ThresholdMovementCohort) -> list[ReportLine]:
    dispersion = (
        f"{mechanism.client_dispersion_delta_fpr.value:.6g}"
        if mechanism.client_dispersion_delta_fpr is not None
        else "unavailable"
    )
    return [
        ReportLine(line)
        for line in [
            f"Movements: {len(mechanism.movements)}",
            f"Availability: `{mechanism.availability.value}`",
            (
                f"Mean Δ FPR: {mechanism.mean_delta_fpr.value:.6g}"
                if mechanism.mean_delta_fpr is not None
                else f"Reason: {mechanism.reason}"
            ),
            f"Client dispersion of Δ FPR: {dispersion}",
        ]
    ]


def _render_threshold_movement_uncertainty(mechanism: ThresholdMovementMultiSeedUncertainty) -> list[ReportLine]:
    across = (
        f"{mechanism.across_seed_dispersion_delta_fpr.value:.6g}"
        if mechanism.across_seed_dispersion_delta_fpr is not None
        else "unavailable"
    )
    mean = (
        f"{mechanism.mean_of_seed_mean_delta_fpr.value:.6g}"
        if mechanism.mean_of_seed_mean_delta_fpr is not None
        else "unavailable"
    )
    return [
        ReportLine(line)
        for line in [
            f"Seed summaries: {len(mechanism.seed_summaries)}",
            f"Availability: `{mechanism.availability.value}`",
            f"Mean of seed-mean Δ FPR: {mean}",
            f"Across-seed dispersion of mean Δ FPR: {across}",
        ]
    ]


def _render_absorption_cohort_result(mechanism: AbsorptionCohortResult) -> list[ReportLine]:
    retention_interval = mechanism.retention_interval
    retention_bca = (
        f"BCa[{retention_interval.lower_bound.value:.6g}, {retention_interval.upper_bound.value:.6g}]"
        if retention_interval is not None
        and retention_interval.lower_bound is not None
        and retention_interval.upper_bound is not None
        else "BCa unavailable"
    )
    return [
        ReportLine(line)
        for line in [
            f"Seeds: {len(mechanism.observations)}",
            f"Decision: `{mechanism.decision.decision.value}`",
            f"Rationale: {mechanism.decision.rationale}",
            (
                f"Mean retention: {mechanism.mean_retention.value:.6g}"
                if mechanism.mean_retention is not None
                else "Mean retention: unavailable"
            ),
            f"Retention BCa interval across seeds: {retention_bca}",
            f"Alternative-route seeds: {mechanism.alternative_route_seed_count.value}",
        ]
    ]


def _render_scientific_decision_result(mechanism: ScientificDecisionResult) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
            f"Decision: `{mechanism.decision.value}`",
            f"Evidence role: `{mechanism.evidence_role.value}`",
            f"Rationale: {mechanism.rationale}",
        ]
    ]


def _interval_table(interval: BootstrapInterval) -> PublicationTable:
    point = f"{interval.point_estimate.value:.6g}" if interval.point_estimate else ""
    evidence = f"BCa outcome={interval.outcome.value}"
    if interval.reason is not None:
        evidence = f"{evidence} reason={interval.reason.value}"
    return PublicationTable(
        title=TableTitle("Paired BCa interval"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=interval.availability,
                rendered_value=TableCellRenderedValue(point),
                evidence=EvidenceText(evidence),
            ),
        ),
    )


def _wilcoxon_table(wilcoxon: WilcoxonResult, rank_biserial: RankBiserialResult) -> PublicationTable:
    p_value = f"{wilcoxon.p_value.value:.6g}" if wilcoxon.p_value else ""
    effect = f"{rank_biserial.value.value:.6g}" if rank_biserial.value else ""
    return PublicationTable(
        title=TableTitle("Secondary paired inference"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=wilcoxon.availability,
                rendered_value=TableCellRenderedValue(p_value),
                evidence=EvidenceText(
                    f"Wilcoxon method={wilcoxon.computation_method.value if wilcoxon.computation_method else 'none'}"
                ),
            ),
            TableCell(
                metric=MetricId.MEAN_FPR,
                availability=rank_biserial.availability,
                rendered_value=TableCellRenderedValue(effect),
                evidence=EvidenceText("matched-pairs rank-biserial"),
            ),
        ),
    )


def _paired_values_table(document: AnalysisDocument) -> PublicationTable:
    if not document.contrasts:
        return PublicationTable(
            title=TableTitle("Paired seed inventory"),
            cells=(
                TableCell(
                    metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                    availability=AvailabilityStatus.UNAVAILABLE,
                    rendered_value=TableCellRenderedValue(""),
                    evidence=EvidenceText(document.unavailable_reason or "no paired contrasts"),
                ),
            ),
        )
    interval_available = document.interval.availability is AvailabilityStatus.AVAILABLE
    decision_not_established = document.decision.decision is ScientificDecision.NOT_ESTABLISHED
    availability = (
        AvailabilityStatus.AVAILABLE
        if interval_available and not decision_not_established
        else AvailabilityStatus.UNAVAILABLE
    )
    point = document.interval.point_estimate
    rendered_value = f"{point.value:.6g}" if point is not None and availability is AvailabilityStatus.AVAILABLE else ""
    evidence = (
        f"{len(document.contrasts)} paired seeds with fixed-score provenance"
        if availability is AvailabilityStatus.AVAILABLE
        else document.unavailable_reason or document.decision.rationale or "confirmatory evidence unavailable"
    )
    return PublicationTable(
        title=TableTitle("Paired seed inventory"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=availability,
                rendered_value=TableCellRenderedValue(rendered_value),
                evidence=EvidenceText(evidence),
            ),
        ),
    )


def _optional_metric(
    value: MetricValue | None,
) -> ReportLine:
    return ReportLine("—" if value is None else f"{value.value:.6g}")


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
        case ScientificDecision.NOT_ESTABLISHED:
            return EvidenceDecision.NOT_ESTABLISHED
        case _:
            return EvidenceDecision.UNSTABLE
