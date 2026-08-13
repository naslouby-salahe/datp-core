from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import singledispatch
from hashlib import sha256
from io import StringIO
from itertools import chain
from pathlib import Path
from typing import Any, TypedDict, cast

from datp_core.analysis.contrasts import ConfirmatoryDescriptiveEffects, PairedContrasts
from datp_core.analysis.descriptive import DescriptiveSummary, PairedDifferenceCounts
from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome, BootstrapInterval
from datp_core.analysis.inference.multiplicity import MultiplicityResult
from datp_core.analysis.inference.precision import ConfirmatoryPrecisionDiagnostics
from datp_core.analysis.inference.sign_test import ExactPairedSignTestResult
from datp_core.analysis.inference.wilcoxon import RankBiserialResult, WilcoxonResult
from datp_core.analysis.influence import LeaveOneDeviceOutDiagnostics
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.mechanisms.absorption import AbsorptionCohortResult
from datp_core.analysis.mechanisms.association import AssociationObservation, AssociationResult
from datp_core.analysis.mechanisms.client_impact import (
    ClientImpactCampaignSummary,
    ClientImpactFraction,
    ClientImpactFractionSummary,
    ClientImpactMagnitudeSummary,
    ClientImpactSeedSummary,
)
from datp_core.analysis.mechanisms.clustering import (
    ClusterAssignmentSwitchSummary,
    ClusterEvidenceRecord,
    ClusterFeatureAblationEvidence,
    ClusterScoreDivergenceResult,
    ClusterSilhouetteResult,
    ClusterStabilityResult,
    GroupedCvFprRecovery,
)
from datp_core.analysis.mechanisms.dispersion import GroupedDispersionResult
from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.analysis.mechanisms.equity_pareto import (
    EquityParetoPoint,
    EquityTargetAttainmentRow,
    EquityUtilityParetoView,
)
from datp_core.analysis.mechanisms.equity_utility import (
    ConfirmatoryEquityUtilityBundle,
    confirmatory_equity_utility_metric,
)
from datp_core.analysis.mechanisms.family_adequacy import FamilyExplanatoryAdequacyResult
from datp_core.analysis.mechanisms.family_recall import FamilyRecallPolicyCampaignSummary, FamilyRecallPolicyComparison
from datp_core.analysis.mechanisms.movement import (
    ThresholdMovement,
    ThresholdMovementCohort,
    ThresholdMovementDirectionCampaign,
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
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    ClaimWording,
    EvidenceRole,
    ExperimentId,
    FileContentText,
    MetricId,
    PopulationId,
    ReportLine,
)
from datp_core.core.numeric import ClusterIndex, MetricValue, PairedObservationCount, Ratio
from datp_core.experiments.anchor.contracts import VerifiedAnchorGateArtifact
from datp_core.presentation.figures import EmpiricalCdfFigureSeries, FigureSpec, render_markdown_figure
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
from datp_core.thresholds.policies.cluster import ClusterMembership

PUBLICATION_FILENAME = "publication.md"
MECHANISM_REPORT_FILENAME = "mechanism_report.md"
PUBLICATION_SOURCE_MANIFEST_FILENAME = "publication_source_manifest.json"
PUBLICATION_SOURCE_DATA_FILENAME = "publication_source_data.csv"
PUBLICATION_DECIMAL_PLACES = 3
PUBLICATION_P_VALUE_SIGNIFICANT_DIGITS = 3
PUBLICATION_P_VALUE_DISPLAY_THRESHOLD = 0.001


class PublicationSourceRow(TypedDict):
    experiment: str
    population: str
    evidence_role: str
    output_kind: str
    output_title: str
    series_label: str
    metric: str
    availability: str
    value_index: str
    x_value: str
    y_value: str
    point_label: str
    evidence: str
    unavailable_reason: str
    client_id: str
    training_seed: str
    score_role: str
    threshold_method: str
    threshold_value: str
    benign_exceedance: str
    attack_acceptance: str
    balanced_accuracy: str
    macro_f1: str


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
_CALIBRATION_SCOPE_BOUNDARY = (
    "## Calibration terminology",
    "",
    "Probability calibration concerns predicted probabilities and may use ECE, Brier score, or NLL. "
    "DATP-Core performs anomaly operating-point calibration: benign score quantiles set decision thresholds, "
    "not probabilities; ECE, Brier score, and NLL therefore are not required endpoint metrics. "
    "Conformal calibration is a separate finite-sample coverage construction and is reported only for its "
    "declared supportive diagnostic.",
)


def export_markdown(
    bundle: PublicationBundle,
    destination: Path,
    *,
    additional_source_files: tuple[Path, ...] = (),
) -> Path:
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
    sections = header + _CALIBRATION_SCOPE_BOUNDARY + permitted + blocked_section + table_section + figure_section
    payload = "\n".join(sections).rstrip() + "\n"
    publication = write_text_atomically(destination, FileContentText(payload))
    source_data = _export_publication_source_data(bundle, destination.parent)
    source_files = (source_data, *additional_source_files)
    _validate_publication_source_files(source_files, destination.parent)
    write_text_atomically(
        destination.parent / PUBLICATION_SOURCE_MANIFEST_FILENAME,
        FileContentText(
            canonical_json_text(
                {
                    "publication": publication.name,
                    "publication_bytes": publication.stat().st_size,
                    "publication_sha256": _sha256_file(publication),
                    "experiment": provenance.experiment.value,
                    "population": provenance.population.value,
                    "evidence_role": provenance.evidence_role.value,
                    "table_count": len(bundle.tables),
                    "figure_count": len(bundle.figures),
                    "sources": tuple(
                        {
                            "filename": source.name,
                            "kind": (
                                "table_figure_source_data"
                                if source == source_data
                                else "additional_figure_table_source"
                            ),
                            "row_count": _source_file_row_count(source),
                            "bytes": source.stat().st_size,
                            "sha256": _sha256_file(source),
                        }
                        for source in source_files
                    ),
                    "claims": tuple(
                        {
                            "status": decision.status.value,
                            "wording": str(decision.wording or ""),
                            "reason": str(decision.reason),
                        }
                        for decision in bundle.claims
                    ),
                }
            )
        ),
    )
    return publication


def _export_publication_source_data(bundle: PublicationBundle, output_directory: Path) -> Path:
    """Emit every rendered table/figure value in a manifest-addressable tidy source table."""

    rows = _publication_source_rows(bundle)
    buffer = StringIO(newline="")
    columns = (
        "experiment",
        "population",
        "evidence_role",
        "output_kind",
        "output_title",
        "series_label",
        "metric",
        "availability",
        "value_index",
        "x_value",
        "y_value",
        "point_label",
        "evidence",
        "unavailable_reason",
        "client_id",
        "training_seed",
        "score_role",
        "threshold_method",
        "threshold_value",
        "benign_exceedance",
        "attack_acceptance",
        "balanced_accuracy",
        "macro_f1",
    )
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(cast(Any, rows))
    return write_text_atomically(
        output_directory / PUBLICATION_SOURCE_DATA_FILENAME, FileContentText(buffer.getvalue())
    )


def _validate_publication_source_files(sources: tuple[Path, ...], output_directory: Path) -> None:
    if len(sources) != len(frozenset(sources)):
        raise ValueError("publication source files must not repeat")
    if any(
        source.parent != output_directory or not source.is_file() or source.is_symlink() or source.stat().st_size == 0
        for source in sources
    ):
        raise ValueError("publication source files must be non-empty regular files in the publication directory")


def _source_file_row_count(source: Path) -> int:
    if source.suffix != ".csv":
        return 1
    with source.open(encoding="utf-8", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def _sha256_file(source: Path) -> str:
    digest = sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _publication_source_rows(bundle: PublicationBundle) -> list[PublicationSourceRow]:
    rows: list[PublicationSourceRow] = []
    for table in bundle.tables:
        for cell in table.cells:
            rows.append(
                _publication_source_row(
                    output_kind="table",
                    output_title=str(table.title),
                    metric=cell.metric.value,
                    availability=cell.availability.value,
                    y_value=str(cell.rendered_value),
                    evidence=str(cell.evidence),
                )
            )
    for figure in bundle.figures:
        for series in figure.series:
            rows.extend(
                _single_axis_source_rows(
                    str(figure.title), series.label, series.metric.value, series.availability.value, series.values
                )
            )
        for series in figure.empirical_cdf_series:
            rows.extend(
                _paired_source_rows(
                    str(figure.title),
                    series.label,
                    f"{series.x_metric.value}:{series.y_metric.value}",
                    series.availability.value,
                    series.x_values,
                    series.y_values,
                    (),
                    str(series.unavailable_reason or ""),
                    client_id=str(series.client_id.value) if series.client_id is not None else "",
                    training_seed=str(series.seed.value) if series.seed is not None else "",
                    score_role=str(series.score_role.value) if series.score_role is not None else "",
                )
            )
            rows.extend(_threshold_overlay_source_rows(str(figure.title), series))
        for series in figure.paired_metric_series:
            rows.extend(
                _paired_source_rows(
                    str(figure.title),
                    series.label,
                    f"{series.x_label}:{series.y_label}",
                    series.availability.value,
                    series.x_values,
                    series.y_values,
                    series.point_labels,
                    str(series.unavailable_reason or ""),
                )
            )
        for index, line in enumerate(figure.causal_map_lines):
            rows.append(
                _publication_source_row(
                    output_kind="figure_causal_map",
                    output_title=str(figure.title),
                    value_index=str(index),
                    evidence=str(line),
                )
            )
    provenance = bundle.provenance
    return [
        {
            **row,
            "experiment": provenance.experiment.value,
            "population": provenance.population.value,
            "evidence_role": provenance.evidence_role.value,
        }
        for row in rows
    ]


def _single_axis_source_rows(
    title: str, label: str, metric: str, availability: str, values: tuple[MetricValue, ...]
) -> list[PublicationSourceRow]:
    return [
        _publication_source_row(
            output_kind="figure_series",
            output_title=title,
            series_label=str(label),
            metric=metric,
            availability=availability,
            value_index=str(index),
            y_value=format(value.value, ".17g"),
        )
        for index, value in enumerate(values)
    ] or [_publication_source_row("figure_series", title, str(label), metric, availability)]


def _paired_source_rows(
    title: str,
    label: str,
    metric: str,
    availability: str,
    x_values: tuple[MetricValue, ...],
    y_values: tuple[MetricValue, ...],
    point_labels: tuple[object, ...],
    unavailable_reason: str,
    *,
    client_id: str = "",
    training_seed: str = "",
    score_role: str = "",
) -> list[PublicationSourceRow]:
    return [
        _publication_source_row(
            output_kind="figure_paired_series",
            output_title=title,
            series_label=str(label),
            metric=metric,
            availability=availability,
            value_index=str(index),
            x_value=format(x_value.value, ".17g"),
            y_value=format(y_value.value, ".17g"),
            point_label=str(point_labels[index]) if point_labels else "",
            unavailable_reason=unavailable_reason,
            client_id=client_id,
            training_seed=training_seed,
            score_role=score_role,
        )
        for index, (x_value, y_value) in enumerate(zip(x_values, y_values, strict=True))
    ] or [
        _publication_source_row(
            "figure_paired_series",
            title,
            str(label),
            metric,
            availability,
            unavailable_reason=unavailable_reason,
            client_id=client_id,
            training_seed=training_seed,
            score_role=score_role,
        )
    ]


def _threshold_overlay_source_rows(title: str, series: EmpiricalCdfFigureSeries) -> list[PublicationSourceRow]:
    """Keep every threshold overlay value in the release's tidy figure source data."""

    return [
        _publication_source_row(
            output_kind="figure_threshold_overlay",
            output_title=title,
            series_label=str(series.label),
            metric=f"{series.x_metric.value}:{series.y_metric.value}",
            availability=series.availability.value,
            value_index=str(index),
            client_id=series.client_id.value if series.client_id is not None else "",
            training_seed=str(series.seed.value) if series.seed is not None else "",
            score_role=series.score_role.value if series.score_role is not None else "",
            threshold_method=overlay.method.value,
            threshold_value=format(overlay.value.value, ".17g"),
            benign_exceedance=_metric_source_value(overlay.benign_exceedance),
            attack_acceptance=_metric_source_value(overlay.attack_acceptance),
            balanced_accuracy=_metric_source_value(overlay.balanced_accuracy),
            macro_f1=_metric_source_value(overlay.macro_f1),
        )
        for index, overlay in enumerate(series.threshold_overlays)
    ]


def _metric_source_value(value: MetricValue | None) -> str:
    return "" if value is None else format(value.value, ".17g")


def _publication_source_row(
    output_kind: str,
    output_title: str,
    series_label: str = "",
    metric: str = "",
    availability: str = "",
    value_index: str = "",
    x_value: str = "",
    y_value: str = "",
    point_label: str = "",
    evidence: str = "",
    unavailable_reason: str = "",
    client_id: str = "",
    training_seed: str = "",
    score_role: str = "",
    threshold_method: str = "",
    threshold_value: str = "",
    benign_exceedance: str = "",
    attack_acceptance: str = "",
    balanced_accuracy: str = "",
    macro_f1: str = "",
) -> PublicationSourceRow:
    return {
        "experiment": "",
        "population": "",
        "evidence_role": "",
        "output_kind": output_kind,
        "output_title": output_title,
        "series_label": series_label,
        "metric": metric,
        "availability": availability,
        "value_index": value_index,
        "x_value": x_value,
        "y_value": y_value,
        "point_label": point_label,
        "evidence": evidence,
        "unavailable_reason": unavailable_reason,
        "client_id": client_id,
        "training_seed": training_seed,
        "score_role": score_role,
        "threshold_method": threshold_method,
        "threshold_value": threshold_value,
        "benign_exceedance": benign_exceedance,
        "attack_acceptance": attack_acceptance,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
    }


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
        _precision_diagnostics_table(document.precision_diagnostics),
        _leave_one_device_out_table(document.leave_one_device_out),
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
    analysis_report = export_analysis_report(document, output_directory / "analysis_report.md")
    return export_markdown(
        bundle,
        output_directory / PUBLICATION_FILENAME,
        additional_source_files=(analysis_report,),
    )


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
    analysis_report = write_text_atomically(output_directory / "external_analysis_report.md", FileContentText(payload))
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
        additional_source_files=(analysis_report,),
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
            "Mean FPR frozen | Mean FPR recal | Drift excess | Recovered | Ratio | Helped | Harmed | Unchanged | "
            "Worst FPR recovery | Interpretation |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
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
            f"{ratio} | {_optional_ratio(recovery.helped_fraction)} | "
            f"{_optional_ratio(recovery.harmed_fraction)} | {_optional_ratio(recovery.unchanged_fraction)} | "
            f"{_optional_metric(recovery.worst_client_fpr_recovery)} | "
            f"`{record.interpretation.value}` |"
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
        spearman = recovery.drift_js_frozen_fpr_spearman
        if spearman is not None:
            lines.append(
                "  - DriftJS→FrozenFPRDeterioration Spearman: "
                + (
                    _format_publication_metric(spearman.value.value)
                    if spearman.value is not None
                    else spearman.availability.value
                )
                + f" (n={spearman.valid_pair_count.value})"
            )
        for trajectory in recovery.client_trajectories:
            lines.append(
                f"  - client `{trajectory.client_id.value}` eligible={trajectory.eligible} "
                f"fpr_static={_optional_metric(trajectory.fpr_static)} "
                f"fpr_frozen={_optional_metric(trajectory.fpr_frozen)} "
                f"fpr_recal={_optional_metric(trajectory.fpr_recalibrated)} "
                f"threshold_drift={_optional_metric(trajectory.threshold_movement_recalibrated)} "
                f"frozen_fpr_deterioration={_optional_metric(trajectory.fpr_movement_frozen)} "
                f"fpr_recovery={_optional_metric(trajectory.fpr_recovery)}"
                f" drift_js={_optional_metric(trajectory.drift_js)}"
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
    analysis_report = write_text_atomically(
        output_directory / "temporal_analysis_report.md",
        FileContentText("\n".join(lines)),
    )
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=document.experiment,
                population=PopulationId.EDGE_TEMPORAL_CLIENTS,
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
        additional_source_files=(
            analysis_report,
            figure_sources.fpr_trajectory_source,
            figure_sources.threshold_movement_source,
            figure_sources.manifest,
        ),
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
    mechanism_report = write_text_atomically(output_directory / MECHANISM_REPORT_FILENAME, FileContentText(payload))
    tables = _mechanism_tables(mechanisms)
    return export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=experiment,
                population=population,
                evidence_role=evidence_role,
            ),
            claims=(_descriptive_evidence_claim(evidence_role),),
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
        additional_source_files=(mechanism_report,),
    )


def _descriptive_evidence_claim(evidence_role: EvidenceRole) -> ClaimDecision:
    match evidence_role:
        case EvidenceRole.MECHANISM:
            wording = ClaimWording("Mechanism evidence is associative and non-confirmatory.")
        case EvidenceRole.SUPPORTIVE:
            wording = ClaimWording("Supportive evidence is non-confirmatory and does not promote a causal claim.")
        case _:
            raise ValueError("mechanism publication requires mechanism or supportive evidence")
    return ClaimDecision(
        status=ClaimStatus.NARROWED,
        wording=wording,
        reason=ClaimReason(f"{evidence_role.value} evidence tier"),
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
    sections.extend(_render_confirmatory_descriptive_effects(document.descriptive_effects))
    if document.precision_diagnostics is not None:
        sections.extend(_render_precision_diagnostics(document.precision_diagnostics))
    if document.leave_one_device_out is not None:
        sections.extend(_render_leave_one_device_out(document.leave_one_device_out))
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
                f"Negative nonzero pairs: {result.negative_pair_count.value}/{result.nonzero_pair_count.value}",
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


def _render_precision_diagnostics(diagnostics: ConfirmatoryPrecisionDiagnostics) -> list[ReportLine]:
    bca_width = (
        "unavailable" if diagnostics.bca_width is None else _format_publication_metric(diagnostics.bca_width.value)
    )
    lines = [
        "## Locked Ten-Seed Precision Diagnostics",
        "",
        f"Full paired mean delta: {_format_publication_metric(diagnostics.full_mean_delta.value)}",
        f"Sample SD of paired deltas: {_format_publication_metric(diagnostics.sample_standard_deviation.value)}",
        f"SE proxy: {_format_publication_metric(diagnostics.standard_error_proxy.value)}",
        f"Normal-reference half-width: {_format_publication_metric(diagnostics.normal_reference_half_width.value)}",
        f"BCa width: {bca_width}",
        f"Minimum LOSO mean: {_format_publication_metric(diagnostics.minimum_leave_one_seed_out_mean.value)}",
        f"Maximum LOSO mean: {_format_publication_metric(diagnostics.maximum_leave_one_seed_out_mean.value)}",
        f"Maximum LOSO shift: {_format_publication_metric(diagnostics.maximum_leave_one_seed_out_shift.value)}",
        "",
        "| Omitted seed | LOSO mean delta |",
        "|---:|---:|",
    ]
    lines.extend(
        f"| {item.omitted_seed.value} | {_format_publication_metric(item.mean_delta.value)} |"
        for item in diagnostics.leave_one_seed_out_means
    )
    return [ReportLine(line) for line in [*lines, ""]]


def _render_leave_one_device_out(diagnostics: LeaveOneDeviceOutDiagnostics) -> list[ReportLine]:
    relative_shift = (
        "UNAVAILABLE_NEAR_ZERO_FULL_EFFECT"
        if diagnostics.relative_maximum_lodo_shift is None
        else _format_publication_metric(diagnostics.relative_maximum_lodo_shift.value)
    )
    nonpositive = ", ".join(device.client_id.value for device in diagnostics.nonpositive_omissions) or "none"
    triggers = ", ".join(trigger.value for trigger in diagnostics.high_influence_triggers) or "none"
    lines = [
        "## Leave-One-Device-Out Influence",
        "",
        f"Full paired mean delta: {_format_publication_metric(diagnostics.full_mean_delta.value)}",
        f"Minimum LODO mean: {_format_publication_metric(diagnostics.minimum_lodo_mean.value)}",
        f"Maximum LODO mean: {_format_publication_metric(diagnostics.maximum_lodo_mean.value)}",
        f"Maximum LODO shift: {_format_publication_metric(diagnostics.maximum_lodo_shift.value)}",
        f"Relative maximum LODO shift: {relative_shift}",
        "Positive-direction retention: " + _format_publication_metric(diagnostics.positive_direction_retention.value),
        f"Nonpositive omissions: {nonpositive}",
        f"LODO_HIGH_INFLUENCE: {'yes' if diagnostics.high_influence else 'no'}",
        f"LODO high-influence triggers: {triggers}",
        "",
        "| Omitted device | Mean delta | Seed deltas |",
        "|---|---:|---|",
    ]
    lines.extend(
        "| "
        + summary.omitted_device.client_id.value
        + " | "
        + _format_publication_metric(summary.mean_delta.value)
        + " | "
        + ", ".join(_format_publication_metric(delta.value) for delta in summary.seed_deltas)
        + " |"
        for summary in diagnostics.device_summaries
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


def _render_confirmatory_descriptive_effects(effects: ConfirmatoryDescriptiveEffects) -> list[ReportLine]:
    relative_values = tuple(item.relative_cv_reduction.value for item in effects.values if item.relative_cv_reduction)
    mean_relative = (
        "unavailable"
        if not relative_values
        else _format_publication_metric(sum(relative_values) / len(relative_values))
    )
    mean_relative_percent = (
        "unavailable"
        if not relative_values
        else _format_publication_metric(100.0 * sum(relative_values) / len(relative_values)) + "%"
    )
    mean_worst = _format_publication_metric(
        sum(item.delta_worst_fpr.value for item in effects.values) / len(effects.values)
    )
    mean_iqr = _format_publication_metric(
        sum(item.delta_iqr_fpr.value for item in effects.values) / len(effects.values)
    )
    lines = [
        "## Confirmatory Descriptive Effects",
        "",
        f"Mean relative CV(FPR) reduction: {mean_relative} ({mean_relative_percent})",
        f"Mean DeltaWorstFPR: {mean_worst}",
        f"Mean DeltaIQR: {mean_iqr}",
        "",
        "| Seed | Relative CV reduction | Relative CV reduction (%) | DeltaWorstFPR | DeltaIQR |",
        "|---:|---:|---:|---:|---:|",
    ]
    lines.extend(
        "| "
        + str(item.seed.value)
        + " | "
        + (
            "unavailable (shared CV(FPR) <= 1e-12)"
            if item.relative_cv_reduction is None
            else _format_publication_metric(item.relative_cv_reduction.value)
        )
        + " | "
        + (
            "unavailable"
            if item.relative_cv_reduction is None
            else _format_publication_metric(100.0 * item.relative_cv_reduction.value) + "%"
        )
        + " | "
        + _format_publication_metric(item.delta_worst_fpr.value)
        + " | "
        + _format_publication_metric(item.delta_iqr_fpr.value)
        + " |"
        for item in effects.values
    )
    return [ReportLine(line) for line in [*lines, ""]]


_MECHANISM_TITLES: dict[type[object], ReportLine] = {
    AssociationResult: ReportLine("heterogeneity_benefit_association"),
    DivergenceResult: ReportLine("jensen_shannon_score_divergence"),
    ClusterStabilityResult: ReportLine("cluster_stability"),
    ClusterAssignmentSwitchSummary: ReportLine("cluster_assignment_switch_frequency"),
    ClusterEvidenceRecord: ReportLine("cluster_evidence"),
    ClusterFeatureAblationEvidence: ReportLine("cluster_feature_ablation"),
    GroupedCvFprRecovery: ReportLine("grouped_cv_fpr_recovery"),
    ClusterSilhouetteResult: ReportLine("cluster_silhouette"),
    ClusterScoreDivergenceResult: ReportLine("cluster_score_divergence"),
    GroupedDispersionResult: ReportLine("grouped_dispersion"),
    ThresholdMovement: ReportLine("threshold_movement"),
    ThresholdMovementCohort: ReportLine("threshold_movement_cohort"),
    ThresholdMovementMultiSeedUncertainty: ReportLine("threshold_movement_across_seed_uncertainty"),
    ThresholdMovementDirectionCampaign: ReportLine("threshold_movement_direction_counts"),
    ClientImpactSeedSummary: ReportLine("natural_device_client_impact"),
    ClientImpactCampaignSummary: ReportLine("natural_device_client_impact_campaign_summary"),
    ConfirmatoryEquityUtilityBundle: ReportLine("confirmatory_equity_utility_bundle"),
    EquityUtilityParetoView: ReportLine("equity_utility_pareto"),
    FamilyRecallPolicyComparison: ReportLine("nbaiot_malware_family_sensitivity"),
    FamilyRecallPolicyCampaignSummary: ReportLine("nbaiot_malware_family_sensitivity_campaign_summary"),
    FamilyExplanatoryAdequacyResult: ReportLine("physical_family_explanatory_adequacy"),
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
    tables: list[PublicationTable] = []
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
            case ConfirmatoryEquityUtilityBundle():
                tables.append(
                    PublicationTable(
                        title=TableTitle("Confirmatory equity–utility companion table"),
                        cells=tuple(
                            TableCell(
                                metric=confirmatory_equity_utility_metric(summary.measure),
                                availability=(
                                    AvailabilityStatus.AVAILABLE
                                    if summary.paired_difference_mean is not None
                                    else AvailabilityStatus.UNAVAILABLE
                                ),
                                rendered_value=TableCellRenderedValue(
                                    ""
                                    if summary.paired_difference_mean is None
                                    else _format_publication_metric(summary.paired_difference_mean.value)
                                ),
                                evidence=EvidenceText(
                                    f"{summary.measure.value}: shared="
                                    + (
                                        "unavailable"
                                        if summary.shared_mean is None
                                        else _format_publication_metric(summary.shared_mean.value)
                                    )
                                    + "; local="
                                    + (
                                        "unavailable"
                                        if summary.local_mean is None
                                        else _format_publication_metric(summary.local_mean.value)
                                    )
                                    + f"; local-minus-shared; paired seeds={summary.paired_seed_count.value}"
                                ),
                            )
                            for summary in mechanism.measures
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
    if cells:
        tables.append(PublicationTable(title=TableTitle("Mechanism scientific values"), cells=tuple(cells)))
    return tuple(tables)


@singledispatch
def _render_one_mechanism(_mechanism: MechanismEvidence) -> list[ReportLine]:
    return [ReportLine("Unhandled mechanism evidence kind")]


@_render_one_mechanism.register
def _render_equity_utility_pareto(mechanism: EquityUtilityParetoView) -> list[ReportLine]:
    lines = [
        ReportLine(
            f"{_pareto_point_label(point)}: "
            f"mean CV(FPR)={_format_publication_metric(point.mean_x.value)} "
            f"mean {mechanism.utility_metric.value}={_format_publication_metric(point.mean_y.value)} "
            f"CV(FPR) BCa={_format_bca_interval(point.x_interval)} "
            f"{mechanism.utility_metric.value} BCa={_format_bca_interval(point.y_interval)} "
            f"nondominated={point.nondominated}"
        )
        for point in mechanism.points
    ]
    lines.extend(
        ReportLine(
            f"{_pareto_target_attainment_label(row)}: "
            f"MeanAbsoluteTargetError="
            f"{_format_publication_metric(row.mean_absolute_target_error.value)} "
            f"WorstAbsoluteTargetError={_format_publication_metric(row.worst_absolute_target_error.value)} "
            f"MeanAbsoluteCalibrationGeneralizationGap="
            f"{_format_publication_metric(row.mean_absolute_calibration_generalization_gap.value)}"
        )
        for row in mechanism.target_attainment
    )
    return lines


def _format_bca_interval(interval: BootstrapInterval) -> str:
    if (
        interval.outcome is BcaOutcome.AVAILABLE
        and interval.lower_bound is not None
        and interval.upper_bound is not None
    ):
        return (
            f"[{_format_publication_metric(interval.lower_bound.value)}, "
            f"{_format_publication_metric(interval.upper_bound.value)}]"
        )
    return interval.outcome.value


def _pareto_policy_label(method: str, shrinkage_weight: float | None) -> str:
    return method if shrinkage_weight is None else f"{method}(lambda={shrinkage_weight:g})"


def _pareto_point_label(point: EquityParetoPoint) -> str:
    return _pareto_policy_label(
        point.threshold_method.value,
        point.shrinkage_weight.value if point.shrinkage_weight else None,
    )


def _pareto_target_attainment_label(row: EquityTargetAttainmentRow) -> str:
    return _pareto_policy_label(
        row.threshold_method.value,
        row.shrinkage_weight.value if row.shrinkage_weight else None,
    )


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
                f"Evidentiary sufficient: {stats.evidentiary_sufficient}",
            ]
        )
        diagnostics = stats.leave_one_out_diagnostics
        lines.extend(
            _render_association_observation(
                index=index,
                observation=observation,
                leverage=stats.leverage[index],
                slope=diagnostics.slopes[index],
                r_squared=diagnostics.r_squared[index],
                influence=diagnostics.influences[index],
                reason=diagnostics.unavailable_reasons[index],
            )
            for index, observation in enumerate(mechanism.observations)
        )
    if mechanism.reason:
        lines.append(f"Reason: {mechanism.reason}")
    return [ReportLine(line) for line in lines]


def _render_association_diagnostic(value: MetricValue | Ratio | None, reason: AnalysisReasonText | None) -> str:
    if value is not None:
        return _format_publication_metric(value.value)
    return f"unavailable ({reason or 'unspecified reason'})"


def _render_association_observation(
    *,
    index: int,
    observation: AssociationObservation,
    leverage: Ratio,
    slope: MetricValue | None,
    r_squared: Ratio | None,
    influence: MetricValue | None,
    reason: AnalysisReasonText | None,
) -> str:
    return (
        f"Observation {index + 1}: seed={observation.seed.value}; experiment={observation.experiment.value}; "
        f"population={observation.population.value}; regime={observation.regime_label}; "
        f"heterogeneity={_format_publication_metric(observation.heterogeneity.value)}; "
        f"benefit={_format_publication_metric(observation.benefit.value)}; "
        f"leverage={_format_publication_metric(leverage.value)}; "
        f"leave-one-out slope={_render_association_diagnostic(slope, reason)}; "
        f"leave-one-out R²={_render_association_diagnostic(r_squared, reason)}; "
        f"slope influence={_render_association_diagnostic(influence, reason)}"
    )


@_render_one_mechanism.register
def _render_divergence_result(mechanism: DivergenceResult) -> list[ReportLine]:
    lines = [
        f"Clients: {len(mechanism.clients)}",
        f"Availability: `{mechanism.availability.value}`",
        f"Score source: `{mechanism.protocol.score_source.value}`",
        f"Shared support: `{mechanism.protocol.shared_support.value}`",
        f"Binning: `{mechanism.protocol.binning.value}` bins={mechanism.protocol.bin_count.value}",
        "Smoothing: none (locked unsmoothed protocol)",
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
def _render_family_explanatory_adequacy(mechanism: FamilyExplanatoryAdequacyResult) -> list[ReportLine]:
    lines = [
        f"Seed: {mechanism.seed.value}",
        f"Within-family pairs: {mechanism.within_family_pair_count.value}",
        f"Between-family pairs: {mechanism.between_family_pair_count.value}",
        "Singleton families: " + ", ".join(item.value for item in mechanism.singleton_families),
    ]
    if mechanism.unavailable_reason is not None:
        lines.append(f"Reason: {mechanism.unavailable_reason}")
    else:
        assert mechanism.within_family_js is not None
        assert mechanism.between_family_js is not None
        assert mechanism.family_separation_js is not None
        assert mechanism.mean_within_family_threshold_sd is not None
        assert mechanism.between_family_threshold_sd is not None
        lines.extend(
            [
                f"Within-family JS: {_format_publication_metric(mechanism.within_family_js.value)}",
                f"Between-family JS: {_format_publication_metric(mechanism.between_family_js.value)}",
                f"Family separation JS: {_format_publication_metric(mechanism.family_separation_js.value)}",
                "Mean within-family threshold SD: "
                f"{_format_publication_metric(mechanism.mean_within_family_threshold_sd.value)}",
                "Between-family threshold SD: "
                f"{_format_publication_metric(mechanism.between_family_threshold_sd.value)}",
            ]
        )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_grouped_cv_fpr_recovery(mechanism: GroupedCvFprRecovery) -> list[ReportLine]:
    lines = [f"Seed: {mechanism.seed.value}", f"Method: `{mechanism.method.value}`"]
    if mechanism.recovery.fraction is None:
        lines.append(f"CV(FPR) recovery: unavailable ({mechanism.recovery.reason})")
    else:
        assert mechanism.shared_cv_fpr is not None
        assert mechanism.grouped_cv_fpr is not None
        assert mechanism.local_cv_fpr is not None
        lines.extend(
            [
                f"Shared CV(FPR): {_format_publication_metric(mechanism.shared_cv_fpr.value)}",
                f"Grouped CV(FPR): {_format_publication_metric(mechanism.grouped_cv_fpr.value)}",
                f"Local CV(FPR): {_format_publication_metric(mechanism.local_cv_fpr.value)}",
                f"CV(FPR) recovery fraction: {_format_publication_metric(mechanism.recovery.fraction.value)}",
            ]
        )
    return [ReportLine(line) for line in lines]


@_render_one_mechanism.register
def _render_cluster_stability_result(mechanism: ClusterStabilityResult) -> list[ReportLine]:
    left_memberships = _render_cluster_memberships(mechanism.left_memberships)
    right_memberships = _render_cluster_memberships(mechanism.right_memberships)
    return [
        ReportLine(line)
        for line in [
            f"ARI: {_format_publication_metric(mechanism.adjusted_rand_index.value)}",
            f"Clients: {len(mechanism.compared_clients)}",
            f"Left cluster sizes: {_render_cluster_sizes(mechanism.left_partition.group_sizes)}",
            f"Right cluster sizes: {_render_cluster_sizes(mechanism.right_partition.group_sizes)}",
            f"Left empty groups: {_render_cluster_indexes(mechanism.left_partition.empty_groups)}",
            f"Right empty groups: {_render_cluster_indexes(mechanism.right_partition.empty_groups)}",
            f"Left singleton groups: {_render_cluster_indexes(mechanism.left_partition.singleton_groups)}",
            f"Right singleton groups: {_render_cluster_indexes(mechanism.right_partition.singleton_groups)}",
            f"Left memberships: {left_memberships}",
            f"Right memberships: {right_memberships}",
        ]
    ]


@_render_one_mechanism.register
def _render_cluster_assignment_switch_summary(mechanism: ClusterAssignmentSwitchSummary) -> list[ReportLine]:
    return [
        ReportLine(line)
        for line in [
            f"Reference seed: {mechanism.reference_seed.value}",
            f"Compared seeds: {', '.join(str(seed.value) for seed in mechanism.compared_seeds)}",
            *(
                f"Client {item.client.client_id.value}: switches={item.switched_seed_count.value}/"
                f"{item.comparison_seed_count.value}; frequency={_format_publication_metric(item.frequency.value)}"
                for item in mechanism.client_frequencies
            ),
        ]
    ]


@_render_one_mechanism.register
def _render_cluster_silhouette_result(mechanism: ClusterSilhouetteResult) -> list[ReportLine]:
    mean = (
        _format_publication_metric(mechanism.mean_silhouette.value)
        if mechanism.mean_silhouette is not None
        else f"unavailable ({mechanism.unavailable_reason})"
    )
    return [
        ReportLine(line)
        for line in [
            f"Seed: {mechanism.seed.value}",
            f"Mean silhouette: {mean}",
            *(
                f"Client {item.client.client_id.value}: cluster={item.cluster_index.value}; silhouette="
                + (
                    _format_publication_metric(item.value.value)
                    if item.value is not None
                    else f"unavailable ({item.unavailable_reason})"
                )
                for item in mechanism.observations
            ),
        ]
    ]


@_render_one_mechanism.register
def _render_cluster_score_divergence_result(mechanism: ClusterScoreDivergenceResult) -> list[ReportLine]:
    within = (
        _format_publication_metric(mechanism.within_cluster_mean.value)
        if mechanism.within_cluster_mean is not None
        else f"unavailable ({mechanism.unavailable_reason})"
    )
    between = (
        _format_publication_metric(mechanism.between_cluster_mean.value)
        if mechanism.between_cluster_mean is not None
        else f"unavailable ({mechanism.unavailable_reason})"
    )
    return [
        ReportLine(line)
        for line in [
            f"Seed: {mechanism.seed.value}",
            f"Within-cluster JS mean: {within}; pairs={mechanism.within_cluster_pair_count.value}",
            f"Between-cluster JS mean: {between}; pairs={mechanism.between_cluster_pair_count.value}",
        ]
    ]


@_render_one_mechanism.register
def _render_cluster_feature_ablation_evidence(mechanism: ClusterFeatureAblationEvidence) -> list[ReportLine]:
    silhouette = (
        _format_publication_metric(mechanism.mean_silhouette.value)
        if mechanism.mean_silhouette is not None
        else f"unavailable ({mechanism.silhouette_unavailable_reason})"
    )
    return [
        ReportLine(line)
        for line in [
            f"Seed: {mechanism.seed.value}",
            f"Omitted fingerprint feature: {mechanism.omitted_feature.value}",
            f"Canonical-versus-ablation ARI: {_format_publication_metric(mechanism.adjusted_rand_index.value)}",
            f"Ablation mean silhouette: {silhouette}",
            f"Ablation CV(FPR): {_format_publication_metric(mechanism.cv_fpr.value)}",
            f"Ablation worst-client FPR: {_format_publication_metric(mechanism.worst_client_fpr.value)}",
        ]
    ]


def _render_cluster_sizes(sizes: tuple[PairedObservationCount, ...]) -> str:
    return ", ".join(str(size.value) for size in sizes) or "none"


def _render_cluster_indexes(indexes: tuple[ClusterIndex, ...]) -> str:
    return ", ".join(str(index.value) for index in indexes) or "none"


def _render_cluster_memberships(memberships: tuple[ClusterMembership, ...]) -> str:
    return (
        "; ".join(
            f"{membership.cluster_index.value}:" + ",".join(client.client_id.value for client in membership.members)
            for membership in memberships
        )
        or "none"
    )


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
def _render_threshold_movement_direction_campaign(mechanism: ThresholdMovementDirectionCampaign) -> list[ReportLine]:
    lines = []
    for counts in mechanism.seed_counts:
        fpr = f"down={counts.fpr_down.value}, same={counts.fpr_same.value}, up={counts.fpr_up.value}"
        tpr = (
            f"down={counts.tpr_down.value}, same={counts.tpr_same.value}, up={counts.tpr_up.value}"
            if counts.tpr_unavailable_reason is None
            and counts.tpr_down is not None
            and counts.tpr_same is not None
            and counts.tpr_up is not None
            else f"unavailable ({counts.tpr_unavailable_reason})"
        )
        lines.append(f"Seed {counts.seed.value}: FPR [{fpr}]; TPR [{tpr}]")
    assert mechanism.median_fpr_down is not None
    assert mechanism.median_fpr_same is not None
    assert mechanism.median_fpr_up is not None
    lines.append(
        "Across-seed median FPR counts: "
        f"down={_format_publication_metric(mechanism.median_fpr_down.value)}, "
        f"same={_format_publication_metric(mechanism.median_fpr_same.value)}, "
        f"up={_format_publication_metric(mechanism.median_fpr_up.value)}"
    )
    if mechanism.tpr_unavailable_reason is None:
        assert mechanism.median_tpr_down is not None
        assert mechanism.median_tpr_same is not None
        assert mechanism.median_tpr_up is not None
        lines.append(
            "Across-seed median TPR counts: "
            f"down={_format_publication_metric(mechanism.median_tpr_down.value)}, "
            f"same={_format_publication_metric(mechanism.median_tpr_same.value)}, "
            f"up={_format_publication_metric(mechanism.median_tpr_up.value)}"
        )
    else:
        lines.append(f"Across-seed median TPR counts: unavailable ({mechanism.tpr_unavailable_reason})")
    return [ReportLine(line) for line in lines]


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
    decision_not_established = document.decision.decision in {
        ScientificDecision.NOT_ESTABLISHED,
        ScientificDecision.CONFIRMATORY_INFERENCE_UNAVAILABLE,
    }
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


def _precision_diagnostics_table(
    diagnostics: ConfirmatoryPrecisionDiagnostics | None,
) -> PublicationTable:
    if diagnostics is None:
        return PublicationTable(
            title=TableTitle("Locked ten-seed precision diagnostics"),
            cells=(
                TableCell(
                    metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                    availability=AvailabilityStatus.UNAVAILABLE,
                    rendered_value=TableCellRenderedValue(""),
                    evidence=EvidenceText("precision diagnostics require available confirmatory paired deltas"),
                ),
            ),
        )
    return PublicationTable(
        title=TableTitle("Locked ten-seed precision diagnostics"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value=TableCellRenderedValue(
                    _format_publication_metric(diagnostics.maximum_leave_one_seed_out_shift.value)
                ),
                evidence=EvidenceText(
                    "SE proxy="
                    + _format_publication_metric(diagnostics.standard_error_proxy.value)
                    + "; normal half-width="
                    + _format_publication_metric(diagnostics.normal_reference_half_width.value)
                    + "; BCa width="
                    + (
                        "unavailable"
                        if diagnostics.bca_width is None
                        else _format_publication_metric(diagnostics.bca_width.value)
                    )
                ),
            ),
        ),
    )


def _leave_one_device_out_table(
    diagnostics: LeaveOneDeviceOutDiagnostics | None,
) -> PublicationTable:
    if diagnostics is None:
        return PublicationTable(
            title=TableTitle("Leave-one-device-out influence"),
            cells=(
                TableCell(
                    metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                    availability=AvailabilityStatus.UNAVAILABLE,
                    rendered_value=TableCellRenderedValue(""),
                    evidence=EvidenceText("leave-one-device-out diagnostic unavailable"),
                ),
            ),
        )
    return PublicationTable(
        title=TableTitle("Leave-one-device-out influence"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value=TableCellRenderedValue(_format_publication_metric(diagnostics.maximum_lodo_shift.value)),
                evidence=EvidenceText(
                    "positive-direction retention="
                    + _format_publication_metric(diagnostics.positive_direction_retention.value)
                    + "; high influence="
                    + ("yes" if diagnostics.high_influence else "no")
                    + "; triggers="
                    + (", ".join(trigger.value for trigger in diagnostics.high_influence_triggers) or "none")
                ),
            ),
        ),
    )


def _optional_metric(
    value: MetricValue | None,
) -> ReportLine:
    return ReportLine("—" if value is None else _format_publication_metric(value.value))


def _optional_ratio(value: Ratio | None) -> ReportLine:
    return ReportLine("—" if value is None else _format_publication_metric(value.value))


_SCIENTIFIC_DECISION_EVIDENCE_DECISIONS: dict[ScientificDecision, EvidenceDecision] = {
    ScientificDecision.SUPPORTED: EvidenceDecision.SUPPORTED,
    ScientificDecision.DIRECTIONAL_INCONCLUSIVE: EvidenceDecision.DIRECTIONAL_INCONCLUSIVE,
    ScientificDecision.OPPOSITE_DIRECTION: EvidenceDecision.REVERSED,
    ScientificDecision.NO_OBSERVED_ADVANTAGE: EvidenceDecision.NULL,
    ScientificDecision.BOUNDARY_RESULT: EvidenceDecision.BOUNDARY,
    ScientificDecision.NOT_ESTABLISHED: EvidenceDecision.NOT_ESTABLISHED,
    ScientificDecision.CONFIRMATORY_INFERENCE_UNAVAILABLE: EvidenceDecision.NOT_ESTABLISHED,
}


def _map_decision(decision: ScientificDecision) -> EvidenceDecision:
    return _SCIENTIFIC_DECISION_EVIDENCE_DECISIONS.get(decision, EvidenceDecision.UNSTABLE)
