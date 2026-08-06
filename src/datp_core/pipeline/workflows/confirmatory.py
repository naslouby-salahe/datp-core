"""Confirmatory campaign execution and paired evidence analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.contrasts import PairedContrast, build_paired_contrast
from datp_core.analysis.mechanisms import (
    AssociationObservation,
    ClientScoreVector,
    MechanismEvidence,
    ThresholdMovementCohort,
    heterogeneity_benefit_association,
    jensen_shannon_from_client_scores,
    summarize_threshold_movements_across_seeds,
    threshold_movements_from_evaluations,
)
from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    ScoreFrameColumn,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.decision.evidence import AnalyzeConfirmatoryEvidenceRequest, analyze_confirmatory_evidence
from datp_core.pipeline.execution.engine import (
    CompletionRecordOutputStore,
    PipelineStageRunner,
    build_campaign,
    execute_campaign,
)
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    federated_training_directory,
)
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.pipeline.scoring.models import FederatedScoreAssetName
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration
from datp_core.protocols.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.reporting.export import (
    export_confirmatory_publication,
    export_mechanism_publication,
)
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
    seeds = tuple(run_confirmatory_seed(seed) for seed in CONFIRMATORY_SEED_COHORT.values)
    return ConfirmatoryCampaignResult(seeds=seeds)


def analyze_confirmatory_campaign(*, anchor_gate_passed: bool = False) -> Path:
    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
    )
    mechanisms = _confirmatory_mechanisms()
    result = analyze_confirmatory_evidence(
        AnalyzeConfirmatoryEvidenceRequest(
            contrasts=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
            output_directory=output,
            overwrite=False,
            mechanisms=mechanisms,
        )
    )
    export_confirmatory_publication(result.document, output, anchor_gate_passed=anchor_gate_passed)
    if mechanisms:
        export_mechanism_publication(
            mechanisms,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output / "mechanisms",
        )
    return output


def _confirmatory_mechanisms() -> tuple[MechanismEvidence, ...]:
    movement_cohorts: list[ThresholdMovementCohort] = []
    association_observations: list[AssociationObservation] = []
    mechanisms: list[MechanismEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        movement = threshold_movements_from_evaluations(
            shared=shared,
            local=local,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        )
        movement_cohorts.append(movement)
        mechanisms.append(movement)
        shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        benefit = MetricValue(shared_cv.value - local_cv.value)
        vectors, score_checksum = _client_score_vectors(shared)
        divergence = jensen_shannon_from_client_scores(vectors, source_score_checksum=score_checksum)
        mechanisms.append(divergence)
        if divergence.aggregate is not None:
            association_observations.append(
                AssociationObservation(
                    seed=seed,
                    experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                    population=PopulationId.NBAIOT_NATURAL_DEVICES,
                    regime_label=f"seed_{seed.value}",
                    heterogeneity=divergence.aggregate,
                    benefit=benefit,
                )
            )
    mechanisms.append(
        summarize_threshold_movements_across_seeds(
            tuple(movement_cohorts),
            required_seed_count=CONFIRMATORY_SEED_COHORT.member_count.value,
        )
    )
    if association_observations:
        mechanisms.append(heterogeneity_benefit_association(tuple(association_observations)))
    return tuple(mechanisms)


def _client_score_vectors(
    document: FederatedEvaluationDocument,
) -> tuple[tuple[ClientScoreVector, ...], Checksum]:
    score_root = (
        federated_training_directory(document.score_coordinate, OUTPUTS_ROOT) / ExecutionArtifactDirectory.SCORES
    )
    vectors: list[ClientScoreVector] = []
    for client_result in sorted(document.clients, key=lambda item: item.client):
        path = score_root / client_result.client.client_id / FederatedScoreAssetName.CALIBRATION.value
        if not path.is_file():
            raise ScientificContractError(
                f"missing persisted benign calibration scores for JS divergence: {path}",
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        scores = tuple(
            MetricValue(float(value))
            for value in pl.read_parquet(path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        )
        if not scores:
            raise ScientificContractError(
                f"empty calibration score vector for client {client_result.client.client_id}",
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        vectors.append(ClientScoreVector(client=client_result.client, scores=scores))
    if len(vectors) < 2:
        raise ScientificContractError("Jensen-Shannon construction requires at least two client score vectors")
    return tuple(vectors), document.fixed_score_evidence.calibration.score_checksum


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
    metric = MetricId.FPR_COEFFICIENT_OF_VARIATION
    return build_paired_contrast(
        left=shared,
        right=local,
        metric=metric,
        left_value=_required_metric(shared, metric),
        right_value=_required_metric(local, metric),
        evidence_role=EvidenceRole.CONFIRMATORY,
    )


def load_fedavg_cv_fpr_effect(training_seed: Seed) -> tuple[MetricValue, MetricValue, MetricValue]:
    """Load FedAvg SHARED/LOCAL population CV(FPR) and Δ from confirmatory evaluation documents."""
    shared = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD))
    local = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
    shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    return shared_cv, local_cv, MetricValue(shared_cv.value - local_cv.value)


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
