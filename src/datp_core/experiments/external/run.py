"""External benign-equity validation and CICIoT applicability-boundary experiments."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from pydantic import TypeAdapter

from datp_core.analysis.contrasts import PairedContrast, SupplementaryPairedAnalysisPlan, build_paired_contrast
from datp_core.analysis.evidence import AnalyzeExternalEvidenceRequest, analyze_external_evidence
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.app.planning import expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.repositories.thresholds import FederatedThresholdAssetName
from datp_core.artifacts.serializers.json import canonical_checksum, serialize_json_model
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ByteCount,
    MetricValue,
    Ratio,
    RowCount,
    ScoreMoment,
    ScoreVariance,
    Seed,
    ThresholdValue,
)
from datp_core.experiments.common.coordinates import ExperimentCoordinate, ExternalTemporalExecutionIdentity
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document, population_metric
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.presentation.export import export_external_publication
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.dispatch import ThresholdConstructionResult
from datp_core.thresholds.variants.federated_statistics import (
    ClientBenignSummary,
    FederatedStatisticsThresholdResult,
)


class BoundedExternalPlanningReason(StrEnum):
    EDGE_BENIGN_EQUITY_PREREQUISITES = "audited Edge benign-equity prerequisites"
    CICIOT_FILE_CLIENT_PREREQUISITES = "audited CICIoT2023 file-client prerequisites"


class BoundedExternalAssetDirectory(StrEnum):
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class BoundedExternalSeedResult:
    experiment: ExperimentId
    evidence_role: EvidenceRole
    population: PopulationId
    partition_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class BoundedExternalCampaignAnalysisResult:
    experiment: ExperimentId
    output_directory: Path
    complete_digest: Checksum


def run_external_validation_seed(
    partition_seed: Seed, *, output_root: Path, overwrite: bool
) -> BoundedExternalSeedResult:
    return _run_seed(
        ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        partition_seed,
        BoundedExternalPlanningReason.EDGE_BENIGN_EQUITY_PREREQUISITES,
        output_root,
        overwrite,
    )


def run_ciciot_boundary_seed(partition_seed: Seed, *, output_root: Path, overwrite: bool) -> BoundedExternalSeedResult:
    return _run_seed(
        ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        partition_seed,
        BoundedExternalPlanningReason.CICIOT_FILE_CLIENT_PREREQUISITES,
        output_root,
        overwrite,
    )


def _run_seed(
    experiment: ExperimentId,
    partition_seed: Seed,
    reason: BoundedExternalPlanningReason,
    output_root: Path,
    overwrite: bool,
) -> BoundedExternalSeedResult:
    declaration = _declaration(experiment)
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(partition_seed,)),
        reason=reason.value,
        output_root=output_root,
        overwrite=overwrite,
    )
    return BoundedExternalSeedResult(
        experiment=declaration.id,
        evidence_role=declaration.role,
        population=declaration.population,
        partition_seed=partition_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def analyze_external_validation_campaign(
    *, output_root: Path, overwrite: bool
) -> BoundedExternalCampaignAnalysisResult:
    return _analyze(ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION, output_root, overwrite)


def analyze_ciciot_boundary_campaign(*, output_root: Path, overwrite: bool) -> BoundedExternalCampaignAnalysisResult:
    return _analyze(ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY, output_root, overwrite)


def _analyze(experiment: ExperimentId, output_root: Path, overwrite: bool) -> BoundedExternalCampaignAnalysisResult:
    declaration = _declaration(experiment)
    base = CONFIRMATORY_INFERENCE_PROTOCOL
    protocol = PairedInferenceProtocol(
        confidence_level=base.confidence_level,
        paired_seed_count=BOUNDED_EVIDENCE_SEED_COHORT.member_count,
        interval_method=base.interval_method,
        bootstrap_replicates=base.bootstrap_replicates,
        statistical_test=base.statistical_test,
        wilcoxon_alternative=base.wilcoxon_alternative,
        wilcoxon_zero_method=base.wilcoxon_zero_method,
        wilcoxon_computation_preference=base.wilcoxon_computation_preference,
        effect_size=base.effect_size,
        multiplicity_correction=base.multiplicity_correction,
        descriptive_lower_quantile=base.descriptive_lower_quantile,
        descriptive_upper_quantile=base.descriptive_upper_quantile,
    )
    plan = SupplementaryPairedAnalysisPlan(
        population=declaration.population,
        evidence_role=declaration.role,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        seed_cohort=BOUNDED_EVIDENCE_SEED_COHORT,
        inference_protocol=protocol,
    )
    contrasts = tuple(_contrast(declaration, seed, output_root) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    output = (
        output_root / BoundedExternalAssetDirectory.ANALYSIS.value / declaration.id.value / declaration.population.value
    )
    if overwrite and output.exists():
        rmtree(output)
    result = analyze_external_evidence(
        AnalyzeExternalEvidenceRequest(
            execution_identity=ExternalTemporalExecutionIdentity(
                experiment=declaration.id,
                population=declaration.population,
                evidence_role=declaration.role,
                temporal_state=None,
            ),
            contrasts=contrasts,
            plan=plan,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
            output_directory=output,
            overwrite=overwrite,
        )
    )
    export_external_publication(result.document, output)
    return BoundedExternalCampaignAnalysisResult(
        experiment=declaration.id,
        output_directory=output,
        complete_digest=result.complete_digest,
    )


class ExternalBenignStatisticsAssetName(StrEnum):
    ROOT = "external_benign_statistics"
    SUMMARY = "external_benign_statistics_summary.json"
    PUBLICATION = "external_benign_statistics.md"
    COMPLETE = "COMPLETE"


class ExternalBenignStatisticsClient(StrictModel):
    client_id: str  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    count: RowCount
    mean: ScoreMoment
    variance: ScoreVariance
    benign_exceedance_count: RowCount | None
    disclosed_bytes: ByteCount


class ExternalBenignStatisticsSummary(StrictModel):
    seed: Seed
    matched_threshold: ThresholdValue
    pooled_quantile_threshold: ThresholdValue
    global_mean: ScoreMoment
    within_client_variance: ScoreVariance
    between_client_variance: ScoreVariance
    full_pooled_variance: ScoreVariance
    between_ratio: Ratio | None
    absolute_threshold_error: AbsoluteThresholdError
    achieved_benign_exceedance: Ratio
    estimated_communication_bytes: ByteCount
    clients: tuple[ExternalBenignStatisticsClient, ...]
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None


class ExternalBenignStatisticsReport(StrictModel):
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    rows: tuple[ExternalBenignStatisticsSummary, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalBenignStatisticsReportResult:
    output_directory: Path
    complete_digest: Checksum


def analyze_external_benign_statistics(*, output_root: Path, overwrite: bool) -> ExternalBenignStatisticsReportResult:
    """Publish the Edge benign-only federated-statistics comparator evidence."""
    declaration = _declaration(ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION)
    output = output_root / ExternalBenignStatisticsAssetName.ROOT / declaration.id.value / declaration.population.value
    if overwrite and output.exists():
        rmtree(output)
    rows = tuple(
        _benign_statistics_summary(declaration, seed, output_root) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values
    )
    manifest = ExternalBenignStatisticsReport(
        experiment=declaration.id,
        population=declaration.population,
        evidence_role=declaration.role,
        rows=rows,
    )
    output.mkdir(parents=True, exist_ok=True)
    serialize_json_model(manifest, output / ExternalBenignStatisticsAssetName.SUMMARY)
    write_text_atomically(
        output / ExternalBenignStatisticsAssetName.PUBLICATION,
        _external_benign_statistics_markdown(manifest),
    )
    digest = canonical_checksum(manifest)
    write_text_atomically(output / ExternalBenignStatisticsAssetName.COMPLETE, digest.value + "\n")
    return ExternalBenignStatisticsReportResult(output_directory=output, complete_digest=digest)


def _benign_statistics_summary(
    declaration: ExperimentDeclaration, seed: Seed, output_root: Path
) -> ExternalBenignStatisticsSummary:
    coordinate = _coordinate(declaration, seed, FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS)
    threshold_path = (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.THRESHOLD
        / FederatedThresholdAssetName.RESULT
    )
    if not threshold_path.is_file():
        raise ScientificContractError(
            ErrorMessage(f"missing FedStats threshold result for Edge seed {seed.value}: {threshold_path}")
        )
    threshold_result = _load_threshold_result(threshold_path)
    if not isinstance(threshold_result, FederatedStatisticsThresholdResult):
        raise ScientificContractError(
            ErrorMessage(f"FedStats threshold result has the wrong type for Edge seed {seed.value}")
        )
    evaluation = load_evaluation_document(
        _evaluation_path(declaration, seed, FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS, output_root)
    )
    return ExternalBenignStatisticsSummary(
        seed=seed,
        matched_threshold=threshold_result.matched_threshold,
        pooled_quantile_threshold=threshold_result.centralized_pooled_quantile_diagnostic,
        global_mean=threshold_result.decomposition.global_mean,
        within_client_variance=threshold_result.decomposition.within_client_variance,
        between_client_variance=threshold_result.decomposition.between_client_variance,
        full_pooled_variance=threshold_result.decomposition.full_pooled_variance,
        between_ratio=threshold_result.decomposition.between_ratio,
        absolute_threshold_error=threshold_result.centralized_attainment_diagnostic.absolute_threshold_error_vs_pooled_quantile,
        achieved_benign_exceedance=threshold_result.centralized_attainment_diagnostic.achieved_exceedance,
        estimated_communication_bytes=threshold_result.estimated_communication_bytes,
        clients=tuple(_benign_statistics_client(summary) for summary in threshold_result.client_summaries),
        cv_fpr=_optional_metric(evaluation, MetricId.FPR_COEFFICIENT_OF_VARIATION),
        worst_client_fpr=_optional_metric(evaluation, MetricId.WORST_CLIENT_FPR),
    )


def _benign_statistics_client(summary: ClientBenignSummary) -> ExternalBenignStatisticsClient:
    return ExternalBenignStatisticsClient(
        client_id=summary.client.client_id,
        count=summary.count,
        mean=summary.mean,
        variance=summary.variance,
        benign_exceedance_count=summary.benign_exceedance_count,
        disclosed_bytes=summary.disclosed_bytes,
    )


def _optional_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue | None:
    result = metric_by_id(document.population.metrics, metric)
    return result.value if result.status is MetricStatus.AVAILABLE else None


def _load_threshold_result(path: Path) -> ThresholdConstructionResult:
    adapter: TypeAdapter[ThresholdConstructionResult] = TypeAdapter(ThresholdConstructionResult)
    return adapter.validate_json(path.read_text(encoding="utf-8"))


def _external_benign_statistics_markdown(manifest: ExternalBenignStatisticsReport) -> str:
    lines = [
        "# DATP-Core External Benign Statistics",
        "",
        f"Experiment: `{manifest.experiment.value}`  ",
        f"Population: `{manifest.population.value}`  ",
        f"Evidence role: `{manifest.evidence_role.value}`  ",
        f"Benign-only comparator: `{FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS.value}`",
        "",
        "Attack outcomes are typed unavailable when the benign-only comparator does not produce them;",
        "no value is fabricated.",
        "",
    ]
    for row in manifest.rows:
        lines.extend(
            (
                f"## Seed {row.seed.value}",
                "",
                "| Quantity | Value |",
                "|---|---:|",
                f"| Matched threshold (estimator) | {row.matched_threshold.value:.6g} |",
                f"| Pooled benign quantile threshold | {row.pooled_quantile_threshold.value:.6g} |",
                f"| Global mean | {row.global_mean.value:.6g} |",
                f"| Within-client variance | {row.within_client_variance.value:.6g} |",
                f"| Between-client variance | {row.between_client_variance.value:.6g} |",
                f"| Full pooled variance | {row.full_pooled_variance.value:.6g} |",
                "| Between-client variance ratio | "
                + (f"{row.between_ratio.value:.6g}" if row.between_ratio is not None else "unavailable")
                + " |",
                f"| Absolute threshold error | {row.absolute_threshold_error.value:.6g} |",
                f"| Achieved benign exceedance | {row.achieved_benign_exceedance.value:.6g} |",
                f"| Estimated communication bytes | {row.estimated_communication_bytes.value:.6g} |",
                "| CV(FPR) | " + (f"{row.cv_fpr.value:.6g}" if row.cv_fpr is not None else "unavailable") + " |",
                "| Worst-client FPR | "
                + (f"{row.worst_client_fpr.value:.6g}" if row.worst_client_fpr is not None else "unavailable")
                + " |",
                "",
                "### Disclosed per-client benign summary",
                "",
                "| Client | n | Mean | Variance | Benign exceedance | Disclosed bytes |",
                "|---|---:|---:|---:|---:|---:|",
            )
        )
        lines.extend(
            (
                f"| {client.client_id} | {client.count.value} | {client.mean.value:.6g} | "
                f"{client.variance.value:.6g} | "
                + (
                    f"{client.benign_exceedance_count.value}"
                    if client.benign_exceedance_count is not None
                    else "unavailable"
                )
                + f" | {client.disclosed_bytes.value} |"
            )
            for client in row.clients
        )
        lines.extend(("",))
    return "\n".join(lines)


def _contrast(declaration: ExperimentDeclaration, seed: Seed, output_root: Path) -> PairedContrast:
    metric = MetricId.FPR_COEFFICIENT_OF_VARIATION
    shared = load_evaluation_document(
        _evaluation_path(declaration, seed, FederatedThresholdMethod.SHARED_THRESHOLD, output_root)
    )
    local = load_evaluation_document(
        _evaluation_path(declaration, seed, FederatedThresholdMethod.LOCAL_THRESHOLD, output_root)
    )
    return build_paired_contrast(
        left=shared,
        right=local,
        metric=metric,
        left_value=_required_metric(shared, metric),
        right_value=_required_metric(local, metric),
        evidence_role=declaration.role,
    )


def _required_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    return population_metric(document, metric)


def _evaluation_path(
    declaration: ExperimentDeclaration,
    seed: Seed,
    method: FederatedThresholdMethod,
    output_root: Path,
) -> Path:
    coordinate = _coordinate(declaration, seed, method)
    path = (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(ErrorMessage(f"missing completed evaluation document: {path}"))
    return path


def _coordinate(
    declaration: ExperimentDeclaration, seed: Seed, method: FederatedThresholdMethod
) -> ExperimentCoordinate:
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage("external evaluation coordinate must resolve exactly once"))
    return matches[0]


def _declaration(experiment: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment)
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage("bounded external experiment must be declared exactly once"), subject=experiment
        )
    declaration = matches[0]
    if declaration.role not in (EvidenceRole.EXTERNAL_VALIDATION, EvidenceRole.APPLICABILITY_BOUNDARY):
        raise ScientificContractError(ErrorMessage("invalid bounded external evidence role"), subject=declaration.role)
    return declaration
