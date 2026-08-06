"""Bounded external and applicability-boundary campaign execution and analysis."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.analysis.contrasts import PairedContrast, SupplementaryPairedAnalysisPlan, build_paired_contrast
from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.decision.evidence import AnalyzeExternalEvidenceRequest, analyze_external_evidence
from datp_core.pipeline.execution.engine import (
    CompletionRecordOutputStore,
    PipelineStageRunner,
    build_campaign,
    execute_campaign,
)
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration, ExternalTemporalExecutionIdentity
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL, PairedInferenceProtocol
from datp_core.reporting.export import export_external_publication
from datp_core.runtime.configuration import OUTPUTS_ROOT


class BoundedExternalPlanningReason(StrEnum):
    EDGE_BENIGN_EQUITY_PREREQUISITES = (
        "the external-validation entry point supplies the audited Edge benign-equity prerequisites"
    )
    CICIOT_FILE_CLIENT_PREREQUISITES = (
        "the applicability-boundary entry point supplies the audited CICIoT2023 file-client prerequisites"
    )


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


def run_external_validation_seed(partition_seed: Seed) -> BoundedExternalSeedResult:
    return _run_bounded_external_seed(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        partition_seed=partition_seed,
        reason=BoundedExternalPlanningReason.EDGE_BENIGN_EQUITY_PREREQUISITES,
    )


def run_ciciot_boundary_seed(partition_seed: Seed) -> BoundedExternalSeedResult:
    return _run_bounded_external_seed(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        partition_seed=partition_seed,
        reason=BoundedExternalPlanningReason.CICIOT_FILE_CLIENT_PREREQUISITES,
    )


def analyze_external_validation_campaign() -> BoundedExternalCampaignAnalysisResult:
    return _analyze_bounded_external_campaign(ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION)


def analyze_ciciot_boundary_campaign() -> BoundedExternalCampaignAnalysisResult:
    return _analyze_bounded_external_campaign(ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY)


def _run_bounded_external_seed(
    *,
    experiment: ExperimentId,
    partition_seed: Seed,
    reason: BoundedExternalPlanningReason,
) -> BoundedExternalSeedResult:
    declaration = _bounded_external_declaration(experiment)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=reason.value,
            ),
        ),
    )
    campaign = build_campaign(plan)
    if not campaign.entries:
        raise ScientificContractError(
            "bounded external planning produced no executable coordinates",
            subject=declaration.id,
        )
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=PipelineStageRunner(),
        output_store=CompletionRecordOutputStore(),
        output_root=OUTPUTS_ROOT,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(
            f"bounded external execution did not complete: {blocked}",
            subject=declaration.id,
        )
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return BoundedExternalSeedResult(
        experiment=declaration.id,
        evidence_role=declaration.role,
        population=declaration.population,
        partition_seed=partition_seed,
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )


def _analyze_bounded_external_campaign(experiment: ExperimentId) -> BoundedExternalCampaignAnalysisResult:
    declaration = _bounded_external_declaration(experiment)
    seed_cohort = BOUNDED_EVIDENCE_SEED_COHORT
    base = CONFIRMATORY_INFERENCE_PROTOCOL
    protocol = PairedInferenceProtocol(
        confidence_level=base.confidence_level,
        seed_cohort=seed_cohort,
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
        seed_cohort=seed_cohort,
        inference_protocol=protocol,
    )
    contrasts = tuple(
        _external_contrast(declaration, seed, MetricId.FPR_COEFFICIENT_OF_VARIATION) for seed in seed_cohort.values
    )
    output = OUTPUTS_ROOT / BoundedExternalAssetDirectory.ANALYSIS / declaration.id.value / declaration.population.value
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
            overwrite=False,
        )
    )
    export_external_publication(result.document, output)
    return BoundedExternalCampaignAnalysisResult(
        experiment=declaration.id,
        output_directory=output,
        complete_digest=result.complete_digest,
    )


def _external_contrast(
    declaration: ExperimentDeclaration,
    partition_seed: Seed,
    metric: MetricId,
) -> PairedContrast:
    shared = load_evaluation_document(
        _evaluation_path(declaration, partition_seed, FederatedThresholdMethod.SHARED_THRESHOLD, metric)
    )
    local = load_evaluation_document(
        _evaluation_path(declaration, partition_seed, FederatedThresholdMethod.LOCAL_THRESHOLD, metric)
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
    partition_seed: Seed,
    method: FederatedThresholdMethod,
    metric: MetricId,
) -> Path:
    coordinate = _external_coordinate(declaration, partition_seed, method, metric)
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(f"missing completed evaluation document: {path}")
    return path


def _external_coordinate(
    declaration: ExperimentDeclaration,
    partition_seed: Seed,
    method: FederatedThresholdMethod,
    metric: MetricId,
) -> ExperimentCoordinate:
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
    )
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method and entry.coordinate.metric is metric
    )
    if len(matches) != 1:
        raise ScientificContractError("external evaluation coordinate must resolve exactly once")
    return matches[0]


def _bounded_external_declaration(experiment: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment)
    if len(matches) != 1:
        raise ScientificContractError(
            "the bounded external experiment must be declared exactly once",
            subject=experiment,
        )
    declaration = matches[0]
    if declaration.role not in (
        EvidenceRole.EXTERNAL_VALIDATION,
        EvidenceRole.APPLICABILITY_BOUNDARY,
    ):
        raise ScientificContractError(
            "bounded external execution accepts only external-validation or applicability-boundary evidence",
            subject=declaration.role,
        )
    return declaration
