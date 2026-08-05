"""Confirmatory campaign execution and paired evidence analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.analysis.contrasts import PairedContrast
from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.evaluation.population import FederatedEvaluationAssetName, FederatedEvaluationDocument
from datp_core.pipeline.decision.evidence import AnalyzeConfirmatoryEvidenceRequest, analyze_confirmatory_evidence
from datp_core.pipeline.execution.engine import CompletionRecordOutputStore, PipelineStageRunner, build_campaign, execute_campaign
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.execution.scoring import load_evaluation_document, population_metric
from datp_core.pipeline.planning import ExperimentCoordinate, PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.runtime.configuration import OUTPUTS_ROOT


class ConfirmatoryAssetDirectory(StrEnum):
    ROOT = "confirmatory"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatorySeedResult:
    training_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatoryCampaignResult:
    seeds: tuple[ConfirmatorySeedResult, ...]


def run_confirmatory_seed(training_seed: Seed) -> ConfirmatorySeedResult:
    declaration = _confirmatory_declaration()
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="the confirmatory entry point supplies the locked natural-device execution prerequisites",
            ),
        ),
    )
    campaign = build_campaign(plan)
    if not campaign.entries:
        raise ScientificContractError("confirmatory planning produced no executable coordinates")
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=PipelineStageRunner(),
        output_store=CompletionRecordOutputStore(),
        output_root=OUTPUTS_ROOT,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(f"confirmatory execution did not complete: {blocked}")
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return ConfirmatorySeedResult(
        training_seed=training_seed,
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )


def run_confirmatory_campaign() -> ConfirmatoryCampaignResult:
    return ConfirmatoryCampaignResult(seeds=tuple(run_confirmatory_seed(seed) for seed in CONFIRMATORY_SEED_COHORT.values))


def analyze_confirmatory_campaign() -> Path:
    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
    )
    analyze_confirmatory_evidence(
        AnalyzeConfirmatoryEvidenceRequest(
            contrasts=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
            output_directory=output,
            overwrite=False,
        )
    )
    return output


def _confirmatory_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    if len(matches) != 1:
        raise ScientificContractError("the confirmatory experiment must be declared exactly once")
    return matches[0]


def _confirmatory_coordinate(training_seed: Seed, method: FederatedThresholdMethod) -> ExperimentCoordinate:
    declaration = _confirmatory_declaration()
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(training_seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError("confirmatory evaluation coordinate must resolve exactly once")
    return matches[0]


def _confirmatory_contrast(training_seed: Seed) -> PairedContrast:
    shared = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD))
    local = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
    if shared.score_coordinate != local.score_coordinate:
        raise ScientificContractError("paired evaluation documents use different training coordinates")
    metric = MetricId.FPR_COEFFICIENT_OF_VARIATION
    return PairedContrast(
        coordinate=shared.score_coordinate,
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=metric,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=_required_metric(shared, metric),
        right_value=_required_metric(local, metric),
    )


def _required_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    return population_metric(document, metric)


def _evaluation_path(training_seed: Seed, method: FederatedThresholdMethod) -> Path:
    coordinate = _confirmatory_coordinate(training_seed, method)
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(f"missing completed evaluation document: {path}")
    return path
