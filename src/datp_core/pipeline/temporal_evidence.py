"""One-shot temporal reference, future recalibration, and analysis execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    TemporalRecoveryResult,
    temporal_recovery,
    validate_frozen_recalibrated_pair,
)
from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.evaluation.controls import build_federated_evaluation_inputs
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.pipeline.analyze_evidence import (
    AnalyzeTemporalEvidenceRequest,
    analyze_temporal_evidence,
)
from datp_core.pipeline.construct_thresholds import ConstructFederatedThresholdsRequest, construct_federated_thresholds
from datp_core.pipeline.evaluate_detector import EvaluateFederatedDetectorRequest, evaluate_federated_detector
from datp_core.pipeline.federated_execution import (
    ExecutionArtifactDirectory,
    FederatedExecutionContext,
    bounded_evidence_seed_directory,
    client_scoring_inputs,
    eligible_calibration_scores,
    matched_static_reference_inputs,
    resolve_execution_context,
    score_selected_checkpoint,
    select_execution_checkpoint,
    training_autoencoder,
    training_feature_names,
)
from datp_core.pipeline.planning import ExperimentCoordinate, expand_experiment_plan
from datp_core.pipeline.scoring.service import FederatedScoreArtifactManifest
from datp_core.populations.capabilities import population_capabilities
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.experiments import EXPERIMENTS, ExternalTemporalExecutionIdentity
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.runtime import OUTPUTS_ROOT
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult


class TemporalArtifactDirectory(StrEnum):
    SCORES = "scores"
    THRESHOLDS = "thresholds"
    EVALUATIONS = "evaluations"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodOutcome:
    method: FederatedThresholdMethod
    fpr_coefficient_of_variation: MetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStateResult:
    state: TemporalState
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]
    provenance: TemporalDeploymentProvenance
    outcomes: tuple[TemporalMethodOutcome, ...]

    def outcome_for(self, method: FederatedThresholdMethod) -> TemporalMethodOutcome:
        matches = tuple(outcome for outcome in self.outcomes if outcome.method is method)
        if len(matches) != 1:
            raise ScientificContractError(
                "temporal state must contain exactly one outcome for each completed method",
                subject=method,
            )
        return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodAnalysisResult:
    method: FederatedThresholdMethod
    recovery: TemporalRecoveryResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalSeedResult:
    partition_seed: Seed
    static_reference: TemporalStateResult
    frozen_future: TemporalStateResult
    recalibrated_future: TemporalStateResult
    analyses: tuple[TemporalMethodAnalysisResult, ...]

    def __post_init__(self) -> None:
        methods = _common_completed_methods(
            self.static_reference,
            self.frozen_future,
            self.recalibrated_future,
        )
        if tuple(item.method for item in self.analyses) != methods:
            raise ValueError("temporal analyses must follow the completed threshold-method order")
        if any(item.recovery.seed != self.partition_seed for item in self.analyses):
            raise ValueError("temporal analysis records must match their partition seed")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalCampaignResult:
    seeds: tuple[TemporalSeedResult, ...]

    def __post_init__(self) -> None:
        expected = BOUNDED_EVIDENCE_SEED_COHORT.values
        observed = tuple(result.partition_seed for result in self.seeds)
        if observed != expected:
            raise ValueError("temporal campaign must contain the complete declared bounded-evidence seed cohort")
        if self.seeds:
            methods = tuple(item.method for item in self.seeds[0].analyses)
            if any(tuple(item.method for item in result.analyses) != methods for result in self.seeds[1:]):
                raise ValueError("temporal campaign seeds must complete the same threshold methods")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStateExecution:
    result: TemporalStateResult


def run_temporal_campaign() -> TemporalCampaignResult:
    return TemporalCampaignResult(
        seeds=tuple(run_temporal_seed(seed) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    )


def run_temporal_seed(partition_seed: Seed) -> TemporalSeedResult:
    declaration = _temporal_declaration()
    static, frozen, recalibrated = _execute_temporal_states(partition_seed, declaration)
    methods = _common_completed_methods(static, frozen, recalibrated)
    analyses = tuple(
        _analyze_temporal_method(
            partition_seed=partition_seed,
            method=method,
            static=static,
            frozen=frozen,
            recalibrated=recalibrated,
        )
        for method in methods
    )
    return TemporalSeedResult(
        partition_seed=partition_seed,
        static_reference=static,
        frozen_future=frozen,
        recalibrated_future=recalibrated,
        analyses=analyses,
    )


def _execute_temporal_states(
    partition_seed: Seed,
    declaration: ExperimentDeclaration,
) -> tuple[TemporalStateResult, TemporalStateResult, TemporalStateResult]:
    frozen_coordinate = _coordinate(partition_seed, TemporalState.FROZEN_FUTURE, declaration)
    context = resolve_execution_context(frozen_coordinate, OUTPUTS_ROOT)
    autoencoder = training_autoencoder(frozen_coordinate.dataset)
    feature_names = training_feature_names(frozen_coordinate.dataset)
    checkpoint = select_execution_checkpoint(
        context,
        autoencoder=autoencoder,
        feature_names=feature_names,
    )
    future_scores = score_selected_checkpoint(
        checkpoint=checkpoint,
        scored_split_protocol=frozen_coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=client_scoring_inputs(context.preprocessing.client_publications, context.clients),
        output_directory=context.training_directory / ExecutionArtifactDirectory.SCORES.value,
        preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
        split_manifest_checksum=context.split_manifest_checksum,
    )
    static_inputs = matched_static_reference_inputs(context, OUTPUTS_ROOT)
    static_coordinate = _coordinate(partition_seed, TemporalState.STATIC_REFERENCE, declaration)
    static_identity = _execution_identity(static_coordinate)
    static_root = bounded_evidence_seed_directory(static_identity, partition_seed, OUTPUTS_ROOT)
    static_scores = score_selected_checkpoint(
        checkpoint=checkpoint,
        scored_split_protocol=static_coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=static_inputs.clients,
        output_directory=static_root / TemporalArtifactDirectory.SCORES.value,
        preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
        split_manifest_checksum=static_inputs.split_manifest_checksum,
    )
    static_provenance = TemporalDeploymentProvenance.from_score_manifest(
        TemporalState.STATIC_REFERENCE,
        static_scores,
    )
    frozen_provenance = TemporalDeploymentProvenance.from_score_manifest(
        TemporalState.FROZEN_FUTURE,
        future_scores,
    )
    recalibrated_provenance = TemporalDeploymentProvenance.from_score_manifest(
        TemporalState.RECALIBRATED_FUTURE,
        future_scores,
    )
    validate_frozen_recalibrated_pair(frozen_provenance, recalibrated_provenance)
    _validate_shared_temporal_detector(static_provenance, frozen_provenance)
    static = _evaluate_state(
        context=context,
        identity=static_identity,
        scores=static_scores,
        calibration_role=PartitionRole.CALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=static_provenance,
    ).result
    frozen = _evaluate_state(
        context=context,
        identity=_execution_identity(frozen_coordinate),
        scores=future_scores,
        calibration_role=PartitionRole.CALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=frozen_provenance,
    ).result
    recalibrated_coordinate = _coordinate(
        partition_seed,
        TemporalState.RECALIBRATED_FUTURE,
        declaration,
    )
    recalibrated = _evaluate_state(
        context=context,
        identity=_execution_identity(recalibrated_coordinate),
        scores=future_scores,
        calibration_role=PartitionRole.FUTURE_RECALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=recalibrated_provenance,
    ).result
    return static, frozen, recalibrated


def _evaluate_state(
    *,
    context: FederatedExecutionContext,
    identity: ExternalTemporalExecutionIdentity,
    scores: FederatedScoreArtifactManifest,
    calibration_role: PartitionRole,
    threshold_methods: tuple[FederatedThresholdMethod, ...],
    provenance: TemporalDeploymentProvenance,
) -> TemporalStateExecution:
    eligible = eligible_calibration_scores(scores, calibration_role)
    capabilities = population_capabilities(context.coordinate.population)
    reference_evidence = None
    completed: list[FederatedThresholdMethod] = []
    outcomes: list[TemporalMethodOutcome] = []
    output_root = bounded_evidence_seed_directory(
        identity,
        context.coordinate.training_seed,
        OUTPUTS_ROOT,
    )
    for method in threshold_methods:
        threshold = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    method,
                    context.coordinate,
                    CANONICAL_QUANTILE,
                    capabilities,
                    eligible,
                    context.family_by_client,
                ),
                output_directory=(
                    output_root / TemporalArtifactDirectory.THRESHOLDS.value / method.value
                ),
                overwrite=False,
                temporal_provenance=provenance,
                temporal_score_manifest=scores,
            )
        ).result
        if isinstance(threshold, ThresholdUnavailableResult):
            continue
        evaluation_inputs = build_federated_evaluation_inputs(scores, method)
        evaluation = evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                score_manifest=scores,
                threshold_result=threshold,
                cohort=evaluation_inputs.cohort,
                fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
                comparison_fixed_score_evidence=reference_evidence,
                evidence_role=identity.evidence_role,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=identity,
                temporal_provenance=provenance,
                temporal_threshold_provenance=provenance,
                output_directory=(
                    output_root / TemporalArtifactDirectory.EVALUATIONS.value / method.value
                ),
                overwrite=False,
            )
        )
        result = metric_by_id(
            evaluation.population.metrics,
            MetricId.FPR_COEFFICIENT_OF_VARIATION,
        )
        if result.status is not MetricStatus.AVAILABLE or result.value is None:
            raise ScientificContractError(
                "temporal evaluation requires available population CV(FPR)",
                subject=method,
            )
        if reference_evidence is None:
            reference_evidence = evaluation_inputs.fixed_score_evidence
        completed.append(method)
        outcomes.append(
            TemporalMethodOutcome(
                method=method,
                fpr_coefficient_of_variation=result.value,
            )
        )
    if not completed:
        raise ScientificContractError(
            "temporal execution produced no evaluable threshold method",
            subject=identity.temporal_state,
        )
    if identity.temporal_state is None:
        raise ScientificContractError("temporal result requires an explicit state")
    return TemporalStateExecution(
        result=TemporalStateResult(
            state=identity.temporal_state,
            completed_threshold_methods=tuple(completed),
            provenance=provenance,
            outcomes=tuple(outcomes),
        )
    )


def _analyze_temporal_method(
    *,
    partition_seed: Seed,
    method: FederatedThresholdMethod,
    static: TemporalStateResult,
    frozen: TemporalStateResult,
    recalibrated: TemporalStateResult,
) -> TemporalMethodAnalysisResult:
    recovery = temporal_recovery(
        seed=partition_seed,
        static_reference_cv=static.outcome_for(method).fpr_coefficient_of_variation,
        frozen_future_cv=frozen.outcome_for(method).fpr_coefficient_of_variation,
        recalibrated_future_cv=recalibrated.outcome_for(method).fpr_coefficient_of_variation,
    )
    analysis = analyze_temporal_evidence(
        AnalyzeTemporalEvidenceRequest(
            static_reference_identity=_identity_for_state(partition_seed, TemporalState.STATIC_REFERENCE),
            frozen_identity=_identity_for_state(partition_seed, TemporalState.FROZEN_FUTURE),
            recalibrated_identity=_identity_for_state(partition_seed, TemporalState.RECALIBRATED_FUTURE),
            static_reference_provenance=static.provenance,
            frozen_provenance=frozen.provenance,
            recalibrated_provenance=recalibrated.provenance,
            records=(recovery,),
            output_directory=_temporal_analysis_directory(partition_seed, method),
            overwrite=False,
        )
    )
    return TemporalMethodAnalysisResult(
        method=method,
        recovery=recovery,
        complete_digest=analysis.complete_digest,
    )


def _validate_shared_temporal_detector(
    static: TemporalDeploymentProvenance,
    frozen: TemporalDeploymentProvenance,
) -> None:
    if (
        static.checkpoint_checksum != frozen.checkpoint_checksum
        or static.preprocessing_state_set_checksum != frozen.preprocessing_state_set_checksum
        or static.coordinate_checksum != frozen.coordinate_checksum
    ):
        raise ScientificContractError(
            "static reference and future states must share one historical detector and preprocessing state",
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )


def _common_completed_methods(
    static: TemporalStateResult,
    frozen: TemporalStateResult,
    recalibrated: TemporalStateResult,
) -> tuple[FederatedThresholdMethod, ...]:
    if not (
        static.completed_threshold_methods
        == frozen.completed_threshold_methods
        == recalibrated.completed_threshold_methods
    ):
        raise ScientificContractError(
            "all temporal states must complete the same declared threshold methods",
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )
    return static.completed_threshold_methods


def _execution_identity(coordinate: ExperimentCoordinate) -> ExternalTemporalExecutionIdentity:
    if coordinate.temporal_state is None:
        raise ScientificContractError("temporal execution requires a temporal state")
    return ExternalTemporalExecutionIdentity(
        experiment=coordinate.experiment,
        population=coordinate.population,
        evidence_role=coordinate.evidence_role,
        temporal_state=coordinate.temporal_state,
    )


def _identity_for_state(partition_seed: Seed, state: TemporalState) -> ExternalTemporalExecutionIdentity:
    return _execution_identity(_coordinate(partition_seed, state, _temporal_declaration()))


def _coordinate(
    partition_seed: Seed,
    state: TemporalState,
    declaration: ExperimentDeclaration,
) -> ExperimentCoordinate:
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
    )
    matches = tuple(entry.coordinate for entry in plan.entries if entry.coordinate.temporal_state is state)
    if not matches:
        raise ScientificContractError(f"no temporal coordinate is declared for {state.value}")
    first = matches[0]
    if any(
        candidate.dataset is not first.dataset
        or candidate.population is not first.population
        or candidate.split_protocol is not first.split_protocol
        or candidate.preprocessing_protocol is not first.preprocessing_protocol
        or candidate.training_model is not first.training_model
        for candidate in matches[1:]
    ):
        raise ScientificContractError(f"temporal coordinates disagree on detector identity for {state.value}")
    return first


def _temporal_analysis_directory(
    partition_seed: Seed,
    method: FederatedThresholdMethod,
) -> Path:
    declaration = _temporal_declaration()
    return (
        OUTPUTS_ROOT
        / "bounded_evidence"
        / declaration.id.value
        / declaration.population.value
        / declaration.role.value
        / str(partition_seed.value)
        / TemporalArtifactDirectory.ANALYSIS.value
        / method.value
    )


def _temporal_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    if len(matches) != 1:
        raise ScientificContractError("the temporal experiment must be declared exactly once")
    return matches[0]
