"""External benign-equity validation and CICIoT applicability-boundary experiments."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.analysis.contrasts import PairedContrast, SupplementaryPairedAnalysisPlan, build_paired_contrast
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.core.numeric import MetricValue, Seed
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.planning import expand_experiment_plan
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.decision.evidence import AnalyzeExternalEvidenceRequest, analyze_external_evidence
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.presentation.export import export_external_publication
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration, ExternalTemporalExecutionIdentity
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL, PairedInferenceProtocol


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
        seed_cohort=BOUNDED_EVIDENCE_SEED_COHORT,
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
        raise ScientificContractError(f"missing completed evaluation document: {path}")
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
        raise ScientificContractError("external evaluation coordinate must resolve exactly once")
    return matches[0]


def _declaration(experiment: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment)
    if len(matches) != 1:
        raise ScientificContractError("bounded external experiment must be declared exactly once", subject=experiment)
    declaration = matches[0]
    if declaration.role not in (EvidenceRole.EXTERNAL_VALIDATION, EvidenceRole.APPLICABILITY_BOUNDARY):
        raise ScientificContractError("invalid bounded external evidence role", subject=declaration.role)
    return declaration
