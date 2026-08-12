from __future__ import annotations

from dataclasses import dataclass
from functools import singledispatch
from itertools import chain
from pathlib import Path

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.descriptive import DescriptiveSummary, PairedDifferenceCounts
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.multiplicity import MultiplicityResult
from datp_core.analysis.inference.sign_test import ExactPairedSignTestResult
from datp_core.analysis.inference.wilcoxon import RankBiserialResult, WilcoxonResult
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.mechanisms.absorption import AbsorptionCohortResult
from datp_core.analysis.mechanisms.association import AssociationResult
from datp_core.analysis.mechanisms.client_impact import (
    ClientImpactCampaignSummary,
    ClientImpactFraction,
    ClientImpactFractionSummary,
    ClientImpactMagnitudeSummary,
    ClientImpactSeedSummary,
)
from datp_core.analysis.mechanisms.clustering import ClusterEvidenceRecord, ClusterStabilityResult
from datp_core.analysis.mechanisms.dispersion import GroupedDispersionResult
from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.analysis.mechanisms.equity_pareto import EquityUtilityParetoView
from datp_core.analysis.mechanisms.equity_utility import ConfirmatoryEquityUtilityBundle
from datp_core.analysis.mechanisms.family_recall import FamilyRecallPolicyCampaignSummary, FamilyRecallPolicyComparison
from datp_core.analysis.mechanisms.movement import (
    ThresholdMovement,
    ThresholdMovementCohort,
    ThresholdMovementMultiSeedUncertainty,
)
from datp_core.analysis.mechanisms.support_burden import (
    CalibrationSupportBurdenCampaignSummary,
    CalibrationSupportBurdenDeviceReport,
    CalibrationSupportBurdenSeedEvidence,
    SupportCorrelationDirectionSummary,
)
from datp_core.analysis.mechanisms.support_strata import (
    CampaignFixedSupportStrata,
    SupportStratumCampaignSummary,
    SupportStratumCrossSeedMetricSummary,
    SupportStratumOutcomeReport,
)
from datp_core.analysis.preparation import AnalysisDocument, ExternalAnalysisDocument, TemporalAnalysisDocument
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
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
from datp_core.presentation.temporal_figures import export_temporal_figure_sources, temporal_publication_figures
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
PUBLICATION_DECIMAL_PLACES = 3
PUBLICATION_P_VALUE_SIGNIFICANT_DIGITS = 3
PUBLICATION_P_VALUE_DISPLAY_THRESHOLD = 0.001


def format_publication_metric(value: float) -> str:
    return f"{value:.{PUBLICATION_DECIMAL_PLACES}f}"


def _format_publication_metric(value: float) -> str:
    return format_publication_metric(value)


def _format_publication_p_value(value: float) -> str:
    if value < PUBLICATION_P_VALUE_DISPLAY_THRESHOLD:
        return "< 0.001"
    return f"{value:.{PUBLICATION_P_VALUE_SIGNIFICANT_DIGITS}g}"


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportProvenance:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole


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
            ),
            claims=(claim,),
            tables=(_interval_table(document.interval),),
            figures=(),
        ),
        output_directory / PUBLICATION_FILENAME,
    )


def export_temporal_publication(document: TemporalAnalysisDocument, output_directory: Path) -> Path:
    figures = temporal_publication_figures(document)
    figure_sources = export_temporal_figure_sources(document, output_directory)
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
        ratio = (
            "undefined"
            if recovery.recovery_ratio is None
            else _format_publication_metric(recovery.recovery_ratio.value)
        )
        mean_static = (
            "—" if recovery.mean_fpr_static is None else _format_publication_metric(recovery.mean_fpr_static.value)
        )
        mean_frozen = (
            "—" if recovery.mean_fpr_frozen is None else _format_publication_metric(recovery.mean_fpr_frozen.value)
        )
        mean_recal = (
            "—"
            if recovery.mean_fpr_recalibrated is None
            else _format_publication_metric(recovery.mean_fpr_recalibrated.value)
        )
        lines.append(
            f"| {recovery.seed.value} | {_format_publication_metric(recovery.static_reference_cv.value)} | "
            f"{_format_publication_metric(recovery.frozen_future_cv.value)} | "
            f"{_format_publication_metric(recovery.recalibrated_future_cv.value)} | "
            f"{mean_static} | {mean_frozen} | {mean_recal} | "
            f"{_format_publication_metric(recovery.drift_excess.value)} | "
            f"{_format_publication_metric(recovery.recovered_amount.value)} | "
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
            f"- seed `{recovery.seed.value}`: coordinate=`{provenance.frozen_future.coordinate}` "
            f"calibration_score_records={len(provenance.frozen_future.calibration_records)} "
            f"evaluation_score_records={len(provenance.frozen_future.evaluation_records)}"
        )
        for trajectory in recovery.client_trajectories:
            lines.append(
                f"  - client `{trajectory.client_id.value}` eligible={trajectory.eligible} "
                f"fpr_static={_optional_metric(trajectory.fpr_static)} "
                f"fpr_frozen={_optional_metric(trajectory.fpr_frozen)} "
                f"fpr_recal={_optional_metric(trajectory.fpr_recalibrated)}"
            )
    lines.append("")
    lines.extend(
        [
            "## Figure reproduction sources",
            "",
            f"- `FIGURE-011`: `{figure_sources.fpr_trajectory_source.name}`",
            f"- `FIGURE-012`: `{figure_sources.threshold_movement_source.name}`",
            f"- source manifest: `{figure_sources.manifest.name}`",
            "",
        ]
    )
    write_text_atomically(output_directory / "temporal_analysis_report.md", FileContentText("\n".join(lines)))
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=document.experiment,
                population=PopulationId.EDGE_TEMPORAL_GROUPS,
                evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
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
            figures=figures,
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
    sections.extend(_render_exact_sign_test(document.exact_sign_test))
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
    point = _format_publication_metric(decision.point_estimate.value) if decision.point_estimate else "unavailable"
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
    lower = _format_publication_metric(interval.lower_bound.value) if interval.lower_bound else "unavailable"
    point = _format_publication_metric(interval.point_estimate.value) if interval.point_estimate else "unavailable"
    upper = _format_publication_metric(interval.upper_bound.value) if interval.upper_bound else "unavailable"
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
        lines.append(f"Bias correction: {_format_publication_metric(interval.adjustment.bias_correction.value)}")
        lines.append(f"Acceleration: {_format_publication_metric(interval.adjustment.acceleration.value)}")
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
        lines.append(f"Mean: {_format_publication_metric(descriptive.statistics.mean.value)}")
        lines.append(f"Median: {_format_publication_metric(descriptive.statistics.median.value)}")
        lines.append(f"Min: {_format_publication_metric(descriptive.statistics.minimum.value)}")
        lines.append(f"Max: {_format_publication_metric(descriptive.statistics.maximum.value)}")
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
        lines.append(f"Statistic: {_format_publication_metric(wilcoxon.statistic.value)}")
    if wilcoxon.p_value:
        lines.append(f"P-value: {_format_publication_p_value(wilcoxon.p_value.value)}")
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
        lines.append(f"Correlation: {_format_publication_metric(rb.value.value)}")
    if rb.positive_rank_sum:
        lines.append(f"Positive rank sum: {_format_publication_metric(rb.positive_rank_sum.value)}")
    if rb.negative_rank_sum:
        lines.append(f"Negative rank sum: {_format_publication_metric(rb.negative_rank_sum.value)}")
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


def _render_exact_sign_test(result: ExactPairedSignTestResult | None) -> list[ReportLine]:
    lines = ["## Exact Paired Sign Test", ""]
    if result is None:
        lines.append("Unavailable: confirmatory paired contrasts are unavailable")
    else:
        lines.extend(
            (
                f"Positive nonzero pairs: {result.positive_pair_count.value}/{result.nonzero_pair_count.value}",
                "Two-sided exact p-value: "
                + (
                    "unavailable"
                    if result.two_sided_p_value is None
                    else _format_publication_metric(result.two_sided_p_value.value)
                ),
            )
        )
    return [ReportLine(line) for line in [*lines, ""]]


def _render_paired_contrasts(contrasts: PairedContrasts) -> list[ReportLine]:
    lines = [
        "## Paired Seed Values",
        "",
        "| Seed | Shared | Local | Delta |",
        "|---|---:|---:|---:|",
    ]
    for contrast in contrasts.values:
        lines.append(
            f"| {contrast.seed.value} | {_format_publication_metric(contrast.left_value.value)} | "
            f"{_format_publication_metric(contrast.right_value.value)} | "
            f"{_format_publication_metric(contrast.delta.value)} |"
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
            f"{_format_publication_p_value(decision.raw_p_value.value)} | "
            f"{_format_publication_p_value(decision.adjusted_p_value.value)} | {rej} |"
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


_MECHANISM_TITLES: dict[type[object], ReportLine] = {
    AssociationResult: ReportLine("heterogeneity_benefit_association"),
    DivergenceResult: ReportLine("jensen_shannon_score_divergence"),
    ClusterStabilityResult: ReportLine("cluster_stability"),
    ClusterEvidenceRecord: ReportLine("cluster_evidence"),
    GroupedDispersionResult: ReportLine("grouped_dispersion"),
    ThresholdMovement: ReportLine("threshold_movement"),
    ThresholdMovementCohort: ReportLine("threshold_movement_cohort"),
    ThresholdMovementMultiSeedUncertainty: ReportLine("threshold_movement_across_seed_uncertainty"),
    ClientImpactSeedSummary: ReportLine("natural_device_client_impact"),
    ClientImpactCampaignSummary: ReportLine("natural_device_client_impact_campaign_summary"),
    ConfirmatoryEquityUtilityBundle: ReportLine("confirmatory_equity_utility_bundle"),
    EquityUtilityParetoView: ReportLine("equity_utility_pareto"),
    FamilyRecallPolicyComparison: ReportLine("nbaiot_malware_family_sensitivity"),
    FamilyRecallPolicyCampaignSummary: ReportLine("nbaiot_malware_family_sensitivity_campaign_summary"),
    CampaignFixedSupportStrata: ReportLine("campaign_fixed_calibration_support_strata"),
    SupportStratumOutcomeReport: ReportLine("support_stratum_seed_outcomes"),
    SupportStratumCampaignSummary: ReportLine("support_stratum_cross_seed_summary"),
    CalibrationSupportBurdenSeedEvidence: ReportLine("calibration_support_burden"),
    CalibrationSupportBurdenCampaignSummary: ReportLine("calibration_support_burden_campaign_summary"),
    CalibrationSupportBurdenDeviceReport: ReportLine("calibration_support_burden_per_device"),
    AbsorptionCohortResult: ReportLine("model_personalization_absorption"),
    ScientificDecisionResult: ReportLine("scientific_decision"),
}


def _mechanism_title(mechanism: MechanismEvidence) -> ReportLine:
    return next(
        (title for mechanism_type, title in _MECHANISM_TITLES.items() if isinstance(mechanism, mechanism_type)),
        ReportLine("mechanism_evidence"),
    )


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
                        rendered_value=TableCellRenderedValue(_format_publication_metric(stats.spearman_rho.value)),
                        evidence=EvidenceText(
                            f"Spearman association n={mechanism.observation_count.value}; "
                            f"slope={_format_publication_metric(stats.regression_slope.value)}; "
                            f"R²={_format_publication_metric(stats.r_squared.value)}; "
                            f"sufficient={stats.evidentiary_sufficient}"
                        ),
                    )
                )
            case DivergenceResult() if mechanism.aggregate is not None:
                cells.append(
                    TableCell(
                        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(_format_publication_metric(mechanism.aggregate.value)),
                        evidence=EvidenceText(
                            f"mean pairwise JS distance (base-2), clients={len(mechanism.clients)}, "
                            f"bins={mechanism.protocol.bin_count.value}"
                        ),
                    )
                )
            case ThresholdMovementCohort() if mechanism.mean_delta_fpr is not None:
                dispersion = (
                    _format_publication_metric(mechanism.client_dispersion_delta_fpr.value)
                    if mechanism.client_dispersion_delta_fpr is not None
                    else "unavailable"
                )
                cells.append(
                    TableCell(
                        metric=MetricId.MEAN_FPR,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(
                            _format_publication_metric(mechanism.mean_delta_fpr.value)
                        ),
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
                        rendered_value=TableCellRenderedValue(
                            _format_publication_metric(mechanism.mean_retention.value)
                        ),
                        evidence=EvidenceText(
                            f"mean CV(FPR) retention; decision={mechanism.decision.decision.value}; "
                            f"seeds={len(mechanism.observations)}; "
                            f"alternative_route_seeds={mechanism.alternative_route_seed_count}"
                        ),
                    )
                )
            case ClusterEvidenceRecord() if mechanism.cv_fpr_equity_recovery.fraction is not None:
                cells.append(
                    TableCell(
                        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                        availability=mechanism.availability,
                        rendered_value=TableCellRenderedValue(
                            _format_publication_metric(mechanism.cv_fpr_equity_recovery.fraction.value)
                        ),
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


@singledispatch
def _render_one_mechanism(_mechanism: MechanismEvidence) -> list[ReportLine]:
    return [ReportLine("Unhandled mechanism evidence kind")]


@_render_one_mechanism.register
def _render_equity_utility_pareto(mechanism: EquityUtilityParetoView) -> list[ReportLine]:
    return [
        ReportLine(
            f"{point.threshold_method.value}: mean CV(FPR)={_format_publication_metric(point.mean_x.value)} "
            f"mean {mechanism.utility_metric.value}={_format_publication_metric(point.mean_y.value)} "
            f"nondominated={point.nondominated}"
        )
        for point in mechanism.points
    ]


@_render_one_mechanism.register
def _render_family_recall_policy_comparison(mechanism: FamilyRecallPolicyComparison) -> list[ReportLine]:
    lines = [f"Seed: {mechanism.seed.value}"]
    for policy in mechanism.policies:
        lines.append(f"Policy: `{policy.threshold_method.value}`")
        for summary in policy.summaries:
            macro_tpr = _format_publication_metric(summary.macro_family_true_positive_rate.value)
            lines.append(
                f"  {summary.family.name} macro TPR={macro_tpr} "
                f"supported_clients={summary.supported_client_count.value}"
            )
        lines.extend(
            f"  client={record.client.client_id.value} family={record.family.name} "
            f"support={record.support_count.value} TPR={_format_publication_metric(record.true_positive_rate.value)} "
            f"FNR={_format_publication_metric(record.false_negative_rate.value)}"
            for record in policy.records
        )
        worst = policy.worst_family_client
        lines.append(
            f"  worst client-family={worst.client.client_id.value}/{worst.family.name} "
            f"TPR={_format_publication_metric(worst.true_positive_rate.value)}"
        )
    for difference in mechanism.shared_differences:
        difference_value = _format_publication_metric(difference.compared_minus_shared_true_positive_rate.value)
        lines.append(
            f"Shared difference: client={difference.client.client_id.value} family={difference.family.name} "
            f"policy={difference.compared_method.value} ΔTPR={difference_value}"
        )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_family_recall_campaign_summary(mechanism: FamilyRecallPolicyCampaignSummary) -> list[ReportLine]:
    lines = [f"Observed seeds: {mechanism.observed_seed_count.value}"]
    lines.extend(
        f"{summary.threshold_method.value}/{summary.family.name}: "
        f"mean={_format_publication_metric(summary.arithmetic_mean.value)} "
        f"median={_format_publication_metric(summary.median.value)} "
        f"min={_format_publication_metric(summary.minimum.value)} "
        f"max={_format_publication_metric(summary.maximum.value)}; "
        f"seed_values={','.join(_format_publication_metric(value.value) for value in summary.seed_values)}"
        for summary in mechanism.macro_summaries
    )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_association_result(mechanism: AssociationResult) -> list[ReportLine]:
    lines = [
        f"Observations: {mechanism.observation_count.value}",
        f"Availability: `{mechanism.availability.value}`",
    ]
    if mechanism.statistics is not None:
        stats = mechanism.statistics
        interval = stats.regression_slope_confidence_interval
        lines.extend(
            [
                f"Spearman rho: {_format_publication_metric(stats.spearman_rho.value)}",
                f"Spearman p: {_format_publication_p_value(stats.spearman_p_value.value)}",
                f"Intercept: {_format_publication_metric(stats.regression_intercept.value)}",
                f"Slope: {_format_publication_metric(stats.regression_slope.value)} "
                f"(SE {_format_publication_metric(stats.regression_slope_standard_error.value)})",
                f"Slope CI: [{_format_publication_metric(interval.lower_bound.value)}, "
                f"{_format_publication_metric(interval.upper_bound.value)}]",
                f"R²: {_format_publication_metric(stats.r_squared.value)}",
                f"Leverage: {', '.join(_format_publication_metric(value.value) for value in stats.leverage)}",
                "Influence: "
                + ", ".join(
                    _format_publication_metric(value.value) for value in stats.leave_one_out_diagnostics.influences
                ),
                f"Evidentiary sufficient: {stats.evidentiary_sufficient}",
            ]
        )
    if mechanism.reason:
        lines.append(f"Reason: {mechanism.reason}")
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_divergence_result(mechanism: DivergenceResult) -> list[ReportLine]:
    lines = [
        f"Clients: {len(mechanism.clients)}",
        f"Availability: `{mechanism.availability.value}`",
        f"Score source: `{mechanism.protocol.score_source.value}`",
        f"Shared support: `{mechanism.protocol.shared_support.value}`",
        f"Binning: `{mechanism.protocol.binning.value}` bins={mechanism.protocol.bin_count.value}",
        f"Smoothing: {_format_publication_metric(mechanism.protocol.smoothing_constant.value)}",
        f"Log base: `{mechanism.protocol.logarithm_base.value}`",
        f"Aggregation: `{mechanism.protocol.aggregation.value}`",
    ]
    if mechanism.aggregate is not None:
        lines.append(f"Aggregate JS distance: {_format_publication_metric(mechanism.aggregate.value)}")
        lines.append(
            "Pairwise values: "
            + ", ".join(
                f"{distance.left_client.client_id.value}/{distance.right_client.client_id.value}="
                f"{_format_publication_metric(distance.value.value)}"
                for distance in mechanism.pairwise_distances
            )
        )
    if mechanism.reason:
        lines.append(f"Reason: {mechanism.reason}")
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_cluster_stability_result(mechanism: ClusterStabilityResult) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
            f"ARI: {_format_publication_metric(mechanism.adjusted_rand_index.value)}",
            f"Clients: {len(mechanism.compared_clients)}",
            f"Left singletons: {len(mechanism.left_partition.singleton_groups)}",
            f"Right empty groups: {len(mechanism.right_partition.empty_groups)}",
        ]
    ]


@_render_one_mechanism.register
def _render_cluster_evidence_record(mechanism: ClusterEvidenceRecord) -> list[ReportLine]:
    equity = (
        _format_publication_metric(mechanism.cv_fpr_equity_recovery.fraction.value)
        if mechanism.cv_fpr_equity_recovery.fraction is not None
        else mechanism.cv_fpr_equity_recovery.reason
    )
    threshold_recovery = (
        _format_publication_metric(mechanism.threshold_dispersion_recovery.fraction.value)
        if mechanism.threshold_dispersion_recovery.fraction is not None
        else mechanism.threshold_dispersion_recovery.reason
    )
    contributing = (
        _format_publication_metric(mechanism.contributing_quantile_dispersion.value)
        if mechanism.contributing_quantile_dispersion is not None
        else (mechanism.dispersion_unavailable_reason or "unavailable")
    )
    effective = (
        _format_publication_metric(mechanism.effective_threshold_dispersion.value)
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


@_render_one_mechanism.register
def _render_grouped_dispersion_result(mechanism: GroupedDispersionResult) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
            f"Availability: `{mechanism.availability.value}`",
            f"Groups: {len(mechanism.groups)}",
            f"Singletons: {sum(group.size.value == 1 for group in mechanism.groups)}",
            f"Empty: {sum(group.size.value == 0 for group in mechanism.groups)}",
            (
                f"Across-group threshold spread: "
                f"{_format_publication_metric(mechanism.across_group_threshold_spread.value)}"
                if mechanism.across_group_threshold_spread is not None
                else f"Reason: {mechanism.reason}"
            ),
        ]
    ]


@_render_one_mechanism.register
def _render_threshold_movement(mechanism: ThresholdMovement) -> list[ReportLine]:
    delta_tpr = (
        _format_publication_metric(mechanism.delta_tpr.value) if mechanism.delta_tpr is not None else "unavailable"
    )
    return [
        ReportLine(line)
        for line in [
            f"Client: `{mechanism.client.client_id.value}`",
            f"Seed: {mechanism.seed.value}",
            f"Δ threshold: {_format_publication_metric(mechanism.delta_threshold.value)}",
            f"Δ FPR: {_format_publication_metric(mechanism.delta_fpr.value)}",
            f"Δ TPR: {delta_tpr}",
        ]
    ]


@_render_one_mechanism.register
def _render_threshold_movement_cohort(mechanism: ThresholdMovementCohort) -> list[ReportLine]:
    dispersion = (
        _format_publication_metric(mechanism.client_dispersion_delta_fpr.value)
        if mechanism.client_dispersion_delta_fpr is not None
        else "unavailable"
    )
    return [
        ReportLine(line)
        for line in [
            f"Movements: {len(mechanism.movements)}",
            f"Availability: `{mechanism.availability.value}`",
            (
                f"Mean Δ FPR: {_format_publication_metric(mechanism.mean_delta_fpr.value)}"
                if mechanism.mean_delta_fpr is not None
                else f"Reason: {mechanism.reason}"
            ),
            f"Client dispersion of Δ FPR: {dispersion}",
        ]
    ]


@_render_one_mechanism.register
def _render_client_impact_seed_summary(mechanism: ClientImpactSeedSummary) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
            f"Seed: {mechanism.seed.value}",
            f"Availability: `{mechanism.availability.value}`",
            f"FPR helped: {_render_client_impact_fraction(mechanism.fpr_helped)}",
            f"FPR harmed: {_render_client_impact_fraction(mechanism.fpr_harmed)}",
            f"FPR unchanged: {_render_client_impact_fraction(mechanism.fpr_unchanged)}",
            f"TPR loss: {_render_client_impact_fraction(mechanism.tpr_loss)}",
            f"Macro-F1 loss: {_render_client_impact_fraction(mechanism.macro_f1_loss)}",
            f"Balanced-accuracy loss: {_render_client_impact_fraction(mechanism.balanced_accuracy_loss)}",
            f"FPR-harm magnitude: {_render_client_impact_magnitude(mechanism.fpr_harm_magnitude)}",
            f"TPR-loss magnitude: {_render_client_impact_magnitude(mechanism.tpr_loss_magnitude)}",
            f"Pareto improved: {_render_client_impact_fraction(mechanism.pareto.pareto_improved)}",
            f"Pareto harmed: {_render_client_impact_fraction(mechanism.pareto.pareto_harmed)}",
            "Trade-off FPR better / TPR worse: "
            + _render_client_impact_fraction(mechanism.pareto.tradeoff_fpr_better_tpr_worse),
            "Trade-off FPR worse / TPR better: "
            + _render_client_impact_fraction(mechanism.pareto.tradeoff_fpr_worse_tpr_better),
            f"No FPR change: {_render_client_impact_fraction(mechanism.pareto.no_fpr_change)}",
        ]
    ]


@_render_one_mechanism.register
def _render_client_impact_campaign_summary(mechanism: ClientImpactCampaignSummary) -> list[ReportLine]:
    lines = [
        ReportLine(line)
        for line in [
            f"Seed summaries: {len(mechanism.seed_summaries)}",
            f"FPR helped: {_render_client_impact_summary(mechanism.fpr_helped)}",
            f"FPR harmed: {_render_client_impact_summary(mechanism.fpr_harmed)}",
            f"FPR unchanged: {_render_client_impact_summary(mechanism.fpr_unchanged)}",
            f"TPR loss: {_render_client_impact_summary(mechanism.tpr_loss)}",
            f"Macro-F1 loss: {_render_client_impact_summary(mechanism.macro_f1_loss)}",
            f"Balanced-accuracy loss: {_render_client_impact_summary(mechanism.balanced_accuracy_loss)}",
            f"Pareto improved: {_render_client_impact_summary(mechanism.pareto_improved)}",
            f"Pareto harmed: {_render_client_impact_summary(mechanism.pareto_harmed)}",
            "Trade-off FPR better / TPR worse: "
            + _render_client_impact_summary(mechanism.tradeoff_fpr_better_tpr_worse),
            "Trade-off FPR worse / TPR better: "
            + _render_client_impact_summary(mechanism.tradeoff_fpr_worse_tpr_better),
            f"No FPR change: {_render_client_impact_summary(mechanism.no_fpr_change)}",
        ]
    ]
    lines.extend((ReportLine("Per-device repeated-seed frequencies:"),))
    lines.extend(
        ReportLine(
            f"- `{frequency.client.client_id.value}`: "
            f"FPR helped={_render_client_impact_fraction(frequency.fpr_help_frequency)}, "
            f"FPR harmed={_render_client_impact_fraction(frequency.fpr_harm_frequency)}, "
            f"TPR loss={_render_client_impact_fraction(frequency.tpr_loss_frequency)}"
        )
        for frequency in mechanism.device_frequencies
    )
    return lines


@_render_one_mechanism.register
def _render_confirmatory_equity_utility_bundle(mechanism: ConfirmatoryEquityUtilityBundle) -> list[ReportLine]:
    lines = [
        "| Measure | Shared mean | Local mean | Local − shared | Paired seeds |",
        "|---|---:|---:|---:|---:|",
    ]
    for summary in mechanism.measures:
        shared = "unavailable" if summary.shared_mean is None else _format_publication_metric(summary.shared_mean.value)
        local = "unavailable" if summary.local_mean is None else _format_publication_metric(summary.local_mean.value)
        difference = (
            "unavailable"
            if summary.paired_difference_mean is None
            else _format_publication_metric(summary.paired_difference_mean.value)
        )
        lines.append(
            f"| {summary.measure.value} | {shared} | {local} | {difference} | {summary.paired_seed_count.value} |"
        )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_campaign_fixed_support_strata(mechanism: CampaignFixedSupportStrata) -> list[ReportLine]:
    if mechanism.availability is AvailabilityStatus.UNAVAILABLE:
        return [ReportLine(f"Unavailable: {mechanism.reason}")]
    lines = ["| Client | Support score | Ascending rank | Stratum |", "|---|---:|---:|---|"]
    lines.extend(
        f"| `{entry.client.client_id.value}` | {_format_publication_metric(entry.support_score.value)} | "
        f"{entry.ascending_rank.value} | `{entry.stratum.value}` |"
        for entry in mechanism.entries
    )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_support_stratum_outcome_report(mechanism: SupportStratumOutcomeReport) -> list[ReportLine]:
    if mechanism.availability is AvailabilityStatus.UNAVAILABLE:
        return [ReportLine(f"Unavailable: {mechanism.reason}")]
    lines = [
        "| Seed | Stratum | Mean FPR relief | FPR helped | FPR harmed | Shared MATE | Local MATE |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {item.seed.value} | `{item.stratum.value}` | {_format_publication_metric(item.mean_fpr_relief.value)} | "
        f"{_format_publication_metric(item.fpr_helped_fraction.value)} | "
        f"{_format_publication_metric(item.fpr_harmed_fraction.value)} | "
        f"{_format_publication_metric(item.shared_mean_absolute_target_error.value)} | "
        f"{_format_publication_metric(item.local_mean_absolute_target_error.value)} |"
        for item in mechanism.outcomes
    )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_support_stratum_campaign_summary(mechanism: SupportStratumCampaignSummary) -> list[ReportLine]:
    if mechanism.availability is AvailabilityStatus.UNAVAILABLE:
        return [ReportLine(f"Unavailable: {mechanism.reason}")]
    lines = [
        "| Stratum | Measure | Mean | Median | Min | Max |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for summary in mechanism.summaries:
        for label, values in (
            ("mean_fpr_relief", summary.mean_fpr_relief),
            ("fpr_helped_fraction", summary.fpr_helped_fraction),
            ("fpr_harmed_fraction", summary.fpr_harmed_fraction),
            ("shared_mean_absolute_target_error", summary.shared_mean_absolute_target_error),
            ("local_mean_absolute_target_error", summary.local_mean_absolute_target_error),
        ):
            lines.append(f"| `{summary.stratum.value}` | {label} | {_render_cross_seed_metric(values)} |")
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_calibration_support_burden(mechanism: CalibrationSupportBurdenSeedEvidence) -> list[ReportLine]:
    if mechanism.support_fpr_spearman is None or mechanism.support_relief_spearman is None:
        return [ReportLine(f"Seed {mechanism.seed.value}: unavailable ({mechanism.reason})")]
    return [
        ReportLine(
            f"Seed {mechanism.seed.value}: support→FPR Spearman="
            f"{_format_publication_metric(mechanism.support_fpr_spearman.value)}; "
            f"support→relief Spearman={_format_publication_metric(mechanism.support_relief_spearman.value)}; "
            f"clients={len(mechanism.clients)}"
        )
    ]


@_render_one_mechanism.register
def _render_calibration_support_burden_campaign(
    mechanism: CalibrationSupportBurdenCampaignSummary,
) -> list[ReportLine]:
    return [
        ReportLine(f"Support→FPR: {_render_correlation_summary(mechanism.support_fpr)}"),
        ReportLine(f"Support→relief: {_render_correlation_summary(mechanism.support_relief)}"),
    ]


@_render_one_mechanism.register
def _render_calibration_support_burden_devices(
    mechanism: CalibrationSupportBurdenDeviceReport,
) -> list[ReportLine]:
    lines = [
        "| Client | Support median | Shared FPR mean/median | Burden mean/median | Relief mean/median |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| `{item.client.client_id.value}` | "
        f"{_format_publication_metric(item.median_source_benign_calibration_count.value)} | "
        f"{_format_publication_metric(item.mean_shared_false_positive_rate.value)}/"
        f"{_format_publication_metric(item.median_shared_false_positive_rate.value)} | "
        f"{_format_publication_metric(item.mean_shared_target_burden.value)}/"
        f"{_format_publication_metric(item.median_shared_target_burden.value)} | "
        f"{_format_publication_metric(item.mean_personalization_relief.value)}/"
        f"{_format_publication_metric(item.median_personalization_relief.value)} |"
        for item in mechanism.devices
    )
    return [ReportLine(line) for line in lines]


def _render_correlation_summary(summary: SupportCorrelationDirectionSummary) -> str:
    if summary.median is None or summary.minimum is None or summary.maximum is None:
        return (
            f"unavailable; valid={summary.valid_seed_count.value}, unavailable={summary.unavailable_seed_count.value}"
        )
    return (
        f"median={_format_publication_metric(summary.median.value)}, "
        f"min={_format_publication_metric(summary.minimum.value)}, "
        f"max={_format_publication_metric(summary.maximum.value)}; "
        f"negative/zero/positive={summary.negative_count.value}/"
        f"{summary.zero_count.value}/{summary.positive_count.value}; "
        f"valid={summary.valid_seed_count.value}, unavailable={summary.unavailable_seed_count.value}"
    )


def _render_cross_seed_metric(summary: SupportStratumCrossSeedMetricSummary) -> str:
    return " | ".join(
        _format_publication_metric(value.value)
        for value in (summary.arithmetic_mean, summary.median, summary.minimum, summary.maximum)
    )


def _render_client_impact_fraction(fraction: ClientImpactFraction) -> str:
    if fraction.value is None or fraction.numerator is None or fraction.denominator is None:
        return f"unavailable ({fraction.reason})"
    return (
        f"{_format_publication_metric(fraction.value.value)} ({fraction.numerator.value}/{fraction.denominator.value})"
    )


def _render_client_impact_summary(summary: ClientImpactFractionSummary) -> str:
    if summary.arithmetic_mean is None:
        return f"unavailable ({summary.unavailable_seed_count.value} unavailable seeds)"
    return (
        f"mean={_format_publication_metric(summary.arithmetic_mean.value)}, "
        f"median={_format_publication_metric(summary.median.value) if summary.median is not None else 'unavailable'}, "
        f"min={_format_publication_metric(summary.minimum.value) if summary.minimum is not None else 'unavailable'}, "
        f"max={_format_publication_metric(summary.maximum.value) if summary.maximum is not None else 'unavailable'}; "
        f"valid={summary.valid_seed_count.value}, unavailable={summary.unavailable_seed_count.value}"
    )


def _render_client_impact_magnitude(summary: ClientImpactMagnitudeSummary) -> str:
    if summary.median is None or summary.maximum is None:
        return f"unavailable ({summary.reason})"
    return (
        f"median={_format_publication_metric(summary.median.value)}, "
        f"max={_format_publication_metric(summary.maximum.value)}"
    )


@_render_one_mechanism.register
def _render_threshold_movement_uncertainty(mechanism: ThresholdMovementMultiSeedUncertainty) -> list[ReportLine]:
    across = (
        _format_publication_metric(mechanism.across_seed_dispersion_delta_fpr.value)
        if mechanism.across_seed_dispersion_delta_fpr is not None
        else "unavailable"
    )
    mean = (
        _format_publication_metric(mechanism.mean_of_seed_mean_delta_fpr.value)
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


@_render_one_mechanism.register
def _render_absorption_cohort_result(mechanism: AbsorptionCohortResult) -> list[ReportLine]:
    retention_interval = mechanism.retention_interval
    retention_bca = (
        f"BCa[{_format_publication_metric(retention_interval.lower_bound.value)}, "
        f"{_format_publication_metric(retention_interval.upper_bound.value)}]"
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
                f"Mean retention: {_format_publication_metric(mechanism.mean_retention.value)}"
                if mechanism.mean_retention is not None
                else "Mean retention: unavailable"
            ),
            f"Retention BCa interval across seeds: {retention_bca}",
            f"Alternative-route seeds: {mechanism.alternative_route_seed_count.value}",
        ]
    ]


@_render_one_mechanism.register
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
    point = _format_publication_metric(interval.point_estimate.value) if interval.point_estimate else ""
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
    p_value = _format_publication_p_value(wilcoxon.p_value.value) if wilcoxon.p_value else ""
    effect = _format_publication_metric(rank_biserial.value.value) if rank_biserial.value else ""
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
    rendered_value = (
        _format_publication_metric(point.value)
        if point is not None and availability is AvailabilityStatus.AVAILABLE
        else ""
    )
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
    return ReportLine("—" if value is None else _format_publication_metric(value.value))


_SCIENTIFIC_DECISION_EVIDENCE_DECISIONS: dict[ScientificDecision, EvidenceDecision] = {
    ScientificDecision.SUPPORTED: EvidenceDecision.SUPPORTED,
    ScientificDecision.DIRECTIONAL_INCONCLUSIVE: EvidenceDecision.DIRECTIONAL_INCONCLUSIVE,
    ScientificDecision.OPPOSITE_DIRECTION: EvidenceDecision.REVERSED,
    ScientificDecision.NO_OBSERVED_ADVANTAGE: EvidenceDecision.NULL,
    ScientificDecision.BOUNDARY_RESULT: EvidenceDecision.BOUNDARY,
    ScientificDecision.NOT_ESTABLISHED: EvidenceDecision.NOT_ESTABLISHED,
}


def _map_decision(decision: ScientificDecision) -> EvidenceDecision:
    return _SCIENTIFIC_DECISION_EVIDENCE_DECISIONS.get(decision, EvidenceDecision.UNSTABLE)
