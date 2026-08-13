from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.analysis.evidence import (
    AnalyzeTemporalEvidenceRequest,
    analyze_temporal_evidence,
)
from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.federated_publication import (
    EvaluateFederatedDetectorRequest,
    evaluate_federated_detector,
)
from datp_core.analysis.metrics.fixed_score_construction import build_federated_evaluation_inputs
from datp_core.analysis.metrics.models import ClientMetricResult, MetricStatus, metric_by_id
from datp_core.analysis.metrics.semantics import metric_value
from datp_core.analysis.temporal import (
    TemporalClientTrajectory,
    TemporalDeploymentProvenance,
    TemporalRecoveryResult,
    TemporalSeedProvenance,
    require_temporal_decision_protocol,
    temporal_drift_js,
    temporal_recovery,
    training_coordinates,
    validate_frozen_recalibrated_pair,
)
from datp_core.app.planning import ExperimentPlan, expand_experiment_plan
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.repositories.thresholds import (
    FederatedThresholdConstructionRequest,
    construct_and_publish_federated_thresholds,
)
from datp_core.core.errors import (
    ErrorMessage,
    ReportEvidenceError,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    AnalysisReasonText,
    EvaluationCohort,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    StageExecutionEvidence,
    TemporalState,
)
from datp_core.core.numeric import ElapsedSeconds, MetricValue, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.data.registry import population_capabilities
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest, FederatedScoreRecord
from datp_core.experiments.common.coordinates import ExperimentCoordinate, ExternalTemporalExecutionIdentity
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, SeedCohort
from datp_core.experiments.execution.checkpoints import train_execution_model
from datp_core.experiments.execution.context import (
    FederatedExecutionContext,
    client_scoring_inputs,
    resolve_execution_context,
    training_autoencoder,
    training_feature_names,
)
from datp_core.experiments.execution.evidence import load_evaluation_document
from datp_core.experiments.execution.layout import (
    ExecutionArtifactDirectory,
    ExecutionRootDirectory,
    bounded_evidence_seed_directory,
)
from datp_core.experiments.execution.matched_reference import matched_static_reference_inputs
from datp_core.experiments.execution.models import (
    ProgressEvent,
    ProgressEventKind,
    ProgressHook,
    StageOutcome,
)
from datp_core.experiments.execution.score_generation import score_terminal_model
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.presentation.export import export_temporal_publication
from datp_core.thresholds.calibration.service import eligible_calibration_scores
from datp_core.thresholds.contracts import ThresholdInfeasibilityReason, ThresholdUnavailableResult
from datp_core.thresholds.dispatch import ThresholdConstructionRequest
from datp_core.thresholds.protocols import (
    CANONICAL_QUANTILE,
    CalibrationSupportRule,
    ClusterThresholdAggregation,
)


class TemporalArtifactDirectory(StrEnum):
    SCORES = "scores"
    THRESHOLDS = "thresholds"
    EVALUATIONS = "evaluations"
    ANALYSIS = "analysis"
    EVIDENCE = "evidence"


class TemporalClientUnavailableReason(StrEnum):
    EXCLUDED_FROM_FPR_EVALUABLE_COHORT = "excluded_from_fpr_evaluable_cohort"
    CLIENT_NOT_EVALUABLE = "client_not_evaluable"
    NOT_FPR_EVALUABLE = "not_fpr_evaluable"


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodUnavailability:
    method: FederatedThresholdMethod
    reason: ThresholdInfeasibilityReason
    detail: AnalysisReasonText


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodOutcome:
    method: FederatedThresholdMethod
    fpr_coefficient_of_variation: MetricValue
    mean_fpr: MetricValue | None
    clients: tuple[ClientMetricResult, ...]
    excluded_clients: tuple[ClientIdentity, ...]
    unavailable_reasons: tuple[AnalysisReasonText, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStateResult:
    state: TemporalState
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]
    provenance: TemporalDeploymentProvenance
    outcomes: tuple[TemporalMethodOutcome, ...]
    unavailable_methods: tuple[TemporalMethodUnavailability, ...]

    def __post_init__(self) -> None:
        if self.provenance.state is not self.state:
            raise ValueError("temporal state result provenance must match its state")
        completed = tuple(item.method for item in self.outcomes)
        unavailable = tuple(item.method for item in self.unavailable_methods)
        if self.completed_threshold_methods != completed:
            raise ValueError("temporal completed methods must exactly match outcome methods")
        if len(completed) != len(frozenset(completed)) or len(unavailable) != len(frozenset(unavailable)):
            raise ValueError("temporal threshold methods must be unique within a state")
        if frozenset(completed) & frozenset(unavailable):
            raise ValueError("temporal threshold method cannot be completed and unavailable")

    def outcome_for(self, method: FederatedThresholdMethod) -> TemporalMethodOutcome:
        matches = tuple(outcome for outcome in self.outcomes if outcome.method is method)
        if len(matches) != 1:
            raise ScientificContractError(
                ErrorMessage("temporal state must contain exactly one outcome for each completed method"),
                subject=method,
            )
        return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodRecovery:
    method: FederatedThresholdMethod
    recovery: TemporalRecoveryResult


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodCampaignAnalysis:
    method: FederatedThresholdMethod
    output_directory: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalSeedResult:
    partition_seed: Seed
    static_reference: TemporalStateResult
    frozen_future: TemporalStateResult
    recalibrated_future: TemporalStateResult
    recoveries: tuple[TemporalMethodRecovery, ...]

    def __post_init__(self) -> None:
        methods = _common_completed_methods(self.static_reference, self.frozen_future, self.recalibrated_future)
        if not methods:
            raise ValueError("temporal seed result requires at least one completed threshold method")
        _require_matching_temporal_evaluation_cohorts(
            self.static_reference,
            self.frozen_future,
            self.recalibrated_future,
            methods,
        )
        if tuple(item.method for item in self.recoveries) != methods:
            raise ValueError("temporal recoveries must follow the completed threshold-method order")
        if any(item.recovery.seed != self.partition_seed for item in self.recoveries):
            raise ValueError("temporal recovery records must match their partition seed")

    def recovery_for(self, method: FederatedThresholdMethod) -> TemporalRecoveryResult:
        matches = tuple(item.recovery for item in self.recoveries if item.method is method)
        if len(matches) != 1:
            raise ScientificContractError(
                ErrorMessage("temporal seed must contain exactly one recovery per method"), subject=method
            )
        return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalCampaignResult:
    seeds: tuple[TemporalSeedResult, ...]
    analyses: tuple[TemporalMethodCampaignAnalysis, ...]

    def __post_init__(self) -> None:
        expected = BOUNDED_EVIDENCE_SEED_COHORT.values
        observed = tuple(result.partition_seed for result in self.seeds)
        if observed != expected:
            raise ValueError("temporal campaign must contain the complete declared bounded-evidence seed cohort")
        if self.seeds:
            methods = tuple(item.method for item in self.seeds[0].recoveries)
            if any(tuple(item.method for item in result.recoveries) != methods for result in self.seeds[1:]):
                raise ValueError("temporal campaign seeds must complete the same threshold methods")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalCoordinateSet:
    static_reference: ExperimentCoordinate
    frozen_future: ExperimentCoordinate
    recalibrated_future: ExperimentCoordinate
    static_reference_methods: tuple[ExperimentCoordinate, ...]
    frozen_future_methods: tuple[ExperimentCoordinate, ...]
    recalibrated_future_methods: tuple[ExperimentCoordinate, ...]

    def for_state(self, state: TemporalState) -> ExperimentCoordinate:
        match state:
            case TemporalState.STATIC_REFERENCE:
                return self.static_reference
            case TemporalState.FROZEN_FUTURE:
                return self.frozen_future
            case TemporalState.RECALIBRATED_FUTURE:
                return self.recalibrated_future

    def for_state_method(
        self,
        state: TemporalState,
        method: FederatedThresholdMethod,
    ) -> ExperimentCoordinate:
        match state:
            case TemporalState.STATIC_REFERENCE:
                coordinates = self.static_reference_methods
            case TemporalState.FROZEN_FUTURE:
                coordinates = self.frozen_future_methods
            case TemporalState.RECALIBRATED_FUTURE:
                coordinates = self.recalibrated_future_methods
        matches = tuple(coordinate for coordinate in coordinates if coordinate.threshold_method is method)
        if len(matches) != 1:
            raise ScientificContractError(
                ErrorMessage(f"temporal state requires exactly one declared coordinate for {method.value}"),
                subject=method,
            )
        return matches[0]


def run_temporal_seed(
    partition_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> TemporalSeedResult:
    declaration = _temporal_declaration()
    coordinates = _temporal_coordinates(partition_seed, declaration)
    if overwrite:
        _clear_temporal_seed_outputs(coordinates, partition_seed, output_root)
    static, frozen, recalibrated = _execute_temporal_states(
        declaration,
        coordinates,
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    methods = _common_completed_methods(static, frozen, recalibrated)
    result = TemporalSeedResult(
        partition_seed=partition_seed,
        static_reference=static,
        frozen_future=frozen,
        recalibrated_future=recalibrated,
        recoveries=tuple(
            TemporalMethodRecovery(
                method=method,
                recovery=_recovery_for_method(
                    partition_seed=partition_seed,
                    declaration=declaration,
                    method=method,
                    static=static,
                    frozen=frozen,
                    recalibrated=recalibrated,
                ),
            )
            for method in methods
        ),
    )
    return result


def load_temporal_seed_result(
    partition_seed: Seed,
    *,
    output_root: Path,
) -> TemporalSeedResult:
    declaration = _temporal_declaration()
    coordinates = _temporal_coordinates(partition_seed, declaration)
    static = _load_state(
        _execution_identity(coordinates.static_reference),
        partition_seed,
        declaration.federated_thresholds,
        output_root,
    )
    frozen = _load_state(
        _execution_identity(coordinates.frozen_future),
        partition_seed,
        declaration.federated_thresholds,
        output_root,
    )
    recalibrated = _load_state(
        _execution_identity(coordinates.recalibrated_future),
        partition_seed,
        declaration.federated_thresholds,
        output_root,
    )
    methods = _common_completed_methods(static, frozen, recalibrated)
    return TemporalSeedResult(
        partition_seed=partition_seed,
        static_reference=static,
        frozen_future=frozen,
        recalibrated_future=recalibrated,
        recoveries=tuple(
            TemporalMethodRecovery(
                method=method,
                recovery=_recovery_for_method(
                    partition_seed=partition_seed,
                    declaration=declaration,
                    method=method,
                    static=static,
                    frozen=frozen,
                    recalibrated=recalibrated,
                ),
            )
            for method in methods
        ),
    )


def _load_state(
    identity: ExternalTemporalExecutionIdentity,
    partition_seed: Seed,
    threshold_methods: tuple[FederatedThresholdMethod, ...],
    output_root: Path,
) -> TemporalStateResult:
    if identity.temporal_state is None:
        raise ScientificContractError(ErrorMessage("temporal result requires an explicit state"))
    state_root = bounded_evidence_seed_directory(identity, partition_seed, output_root)
    completed: list[FederatedThresholdMethod] = []
    outcomes: list[TemporalMethodOutcome] = []
    provenance: TemporalDeploymentProvenance | None = None
    for method in threshold_methods:
        document_path = (
            state_root
            / TemporalArtifactDirectory.EVALUATIONS.value
            / method.value
            / FederatedEvaluationAssetName.DOCUMENT.value
        )
        if not document_path.is_file():
            continue
        document = load_evaluation_document(document_path)
        if document.temporal_provenance is None:
            raise ReportEvidenceError(
                ErrorMessage("persisted temporal evaluation is missing its temporal provenance"), subject=method
            )
        if provenance is None:
            provenance = document.temporal_provenance
        elif provenance != document.temporal_provenance:
            raise ReportEvidenceError(
                ErrorMessage("persisted temporal evaluations for one state must share one provenance"),
                subject=method,
            )
        cv_fpr = metric_by_id(document.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        if cv_fpr.status is not MetricStatus.AVAILABLE or cv_fpr.value is None:
            raise ReportEvidenceError(
                ErrorMessage("persisted temporal evaluation requires available population CV(FPR)"), subject=method
            )
        mean_metric = metric_by_id(document.population.metrics, MetricId.MEAN_FPR)
        mean_fpr = mean_metric.value if mean_metric.status is MetricStatus.AVAILABLE else None
        if not document.clients:
            raise ReportEvidenceError(
                ErrorMessage("persisted temporal evaluation requires non-empty client metrics"), subject=method
            )
        completed.append(method)
        outcomes.append(
            TemporalMethodOutcome(
                method=method,
                fpr_coefficient_of_variation=cv_fpr.value,
                mean_fpr=mean_fpr,
                clients=document.clients,
                excluded_clients=document.population.excluded_clients,
                unavailable_reasons=_cohort_unavailable_reasons(document.cohort),
            )
        )
    if not completed:
        raise ReportEvidenceError(
            ErrorMessage(f"no persisted temporal evaluation evidence for {identity.temporal_state.value}"),
            subject=identity.temporal_state,
        )
    if provenance is None:
        raise ReportEvidenceError(ErrorMessage("temporal state requires provenance"), subject=identity.temporal_state)
    return TemporalStateResult(
        state=identity.temporal_state,
        completed_threshold_methods=tuple(completed),
        provenance=provenance,
        outcomes=tuple(outcomes),
        unavailable_methods=(),
    )


def analyze_temporal_campaign(
    campaign: TemporalCampaignResult,
    *,
    output_root: Path,
    overwrite: bool,
) -> tuple[TemporalMethodCampaignAnalysis, ...]:
    if not campaign.seeds:
        raise ScientificContractError(ErrorMessage("temporal campaign analysis requires completed seed results"))
    _validate_campaign_recovery_provenance(campaign)
    _validate_campaign_shared_detector_identity(campaign)
    declaration = _temporal_declaration()
    return tuple(
        _publish_temporal_method_campaign(
            method=item.method,
            campaign=campaign,
            declaration=declaration,
            output_root=output_root,
            overwrite=overwrite,
        )
        for item in campaign.seeds[0].recoveries
    )


def _clear_temporal_seed_outputs(
    coordinates: TemporalCoordinateSet,
    partition_seed: Seed,
    output_root: Path,
) -> None:
    for state in TemporalState:
        coordinate = coordinates.for_state(state)
        directory = bounded_evidence_seed_directory(_execution_identity(coordinate), partition_seed, output_root)
        if directory.exists():
            rmtree(directory)


def _recovery_for_method(
    *,
    partition_seed: Seed,
    declaration: ExperimentDeclaration,
    method: FederatedThresholdMethod,
    static: TemporalStateResult,
    frozen: TemporalStateResult,
    recalibrated: TemporalStateResult,
) -> TemporalRecoveryResult:
    static_outcome = static.outcome_for(method)
    frozen_outcome = frozen.outcome_for(method)
    recalibrated_outcome = recalibrated.outcome_for(method)
    trajectories = _build_client_trajectories(
        seed=partition_seed,
        method=method,
        static_outcome=static_outcome,
        frozen_outcome=frozen_outcome,
        recalibrated_outcome=recalibrated_outcome,
        static_calibration_records=static.provenance.calibration_records,
        future_recalibration_records=recalibrated.provenance.calibration_records,
    )
    if not trajectories:
        raise ScientificContractError(
            ErrorMessage(
                "temporal recovery requires non-empty client trajectories when evaluations "
                f"exist (seed={partition_seed.value})"
            ),
            subject=method,
        )
    provenance = TemporalSeedProvenance(
        seed=partition_seed,
        experiment=declaration.id,
        population=declaration.population,
        threshold_method=method,
        static_reference=static.provenance,
        frozen_future=frozen.provenance,
        recalibrated_future=recalibrated.provenance,
        excluded_clients=_union_clients(
            static_outcome.excluded_clients,
            frozen_outcome.excluded_clients,
            recalibrated_outcome.excluded_clients,
        ),
        unavailable_reasons=_union_text(
            static_outcome.unavailable_reasons,
            frozen_outcome.unavailable_reasons,
            recalibrated_outcome.unavailable_reasons,
        ),
    )
    return temporal_recovery(
        seed=partition_seed,
        experiment=declaration.id,
        threshold_method=method,
        static_reference_cv=static_outcome.fpr_coefficient_of_variation,
        frozen_future_cv=frozen_outcome.fpr_coefficient_of_variation,
        recalibrated_future_cv=recalibrated_outcome.fpr_coefficient_of_variation,
        decision_protocol=require_temporal_decision_protocol(),
        mean_fpr_static=static_outcome.mean_fpr,
        mean_fpr_frozen=frozen_outcome.mean_fpr,
        mean_fpr_recalibrated=recalibrated_outcome.mean_fpr,
        provenance=provenance,
        client_trajectories=trajectories,
    )


def _execute_temporal_states(
    declaration: ExperimentDeclaration,
    coordinates: TemporalCoordinateSet,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> tuple[TemporalStateResult, TemporalStateResult, TemporalStateResult]:
    frozen_coordinate = coordinates.frozen_future
    context = resolve_execution_context(frozen_coordinate, output_root)
    autoencoder = training_autoencoder(frozen_coordinate.dataset)
    feature_names = training_feature_names(frozen_coordinate.dataset)
    training = train_execution_model(context, autoencoder=autoencoder, feature_names=feature_names)
    future_scores = score_terminal_model(
        training=training,
        scored_split_protocol=frozen_coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=client_scoring_inputs(context.preprocessing.client_publications, context.clients),
        output_directory=context.training_directory / ExecutionArtifactDirectory.SCORES.value,
    )
    static_inputs = matched_static_reference_inputs(context, output_root)
    static_coordinate = coordinates.static_reference
    static_identity = _execution_identity(static_coordinate)
    static_root = bounded_evidence_seed_directory(static_identity, static_coordinate.training_seed, output_root)
    static_scores = score_terminal_model(
        training=training,
        scored_split_protocol=static_coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=static_inputs.clients,
        output_directory=static_root / TemporalArtifactDirectory.SCORES.value,
    )
    static_provenance = TemporalDeploymentProvenance.from_score_manifest(TemporalState.STATIC_REFERENCE, static_scores)
    frozen_provenance = TemporalDeploymentProvenance.from_score_manifest(TemporalState.FROZEN_FUTURE, future_scores)
    recalibrated_provenance = TemporalDeploymentProvenance.from_score_manifest(
        TemporalState.RECALIBRATED_FUTURE, future_scores
    )
    validate_frozen_recalibrated_pair(frozen_provenance, recalibrated_provenance)
    _validate_shared_temporal_detector(static_provenance, frozen_provenance)
    _require_common_temporal_eligibility_cohort(static_scores, future_scores)

    def _run_state(
        identity: ExternalTemporalExecutionIdentity,
        coordinate: ExperimentCoordinate,
        scores: FederatedScoreArtifactManifest,
        calibration_role: PartitionRole,
        provenance: TemporalDeploymentProvenance,
    ) -> TemporalStateResult:
        if progress is not None:
            progress.emit(
                ProgressEvent(
                    kind=ProgressEventKind.COORDINATE_BEGIN,
                    coordinate=coordinate,
                    detail=StageExecutionEvidence(
                        f"temporal state {identity.temporal_state.value if identity.temporal_state else 'unknown'}"
                    ),
                )
            )
        started = time.monotonic()
        result = _evaluate_state(
            context=context,
            method_coordinates=tuple(
                coordinates.for_state_method(identity.temporal_state, method)
                for method in declaration.federated_thresholds
            )
            if identity.temporal_state is not None
            else (),
            identity=identity,
            scores=scores,
            calibration_role=calibration_role,
            threshold_methods=declaration.federated_thresholds,
            provenance=provenance,
            output_root=output_root,
            overwrite=overwrite,
        )
        if progress is not None:
            progress.emit(
                ProgressEvent(
                    kind=ProgressEventKind.COORDINATE_END,
                    coordinate=coordinate,
                    outcome=StageOutcome.COMPLETED,
                    detail=StageExecutionEvidence(
                        f"temporal state {identity.temporal_state.value if identity.temporal_state else 'unknown'}"
                    ),
                    elapsed_seconds=ElapsedSeconds(time.monotonic() - started),
                )
            )
        return result

    static = _run_state(
        static_identity,
        static_coordinate,
        static_scores,
        PartitionRole.CALIBRATION,
        static_provenance,
    )
    frozen = _run_state(
        _execution_identity(frozen_coordinate),
        frozen_coordinate,
        future_scores,
        PartitionRole.CALIBRATION,
        frozen_provenance,
    )
    recalibrated = _run_state(
        _execution_identity(coordinates.recalibrated_future),
        coordinates.recalibrated_future,
        future_scores,
        PartitionRole.FUTURE_RECALIBRATION,
        recalibrated_provenance,
    )
    return static, frozen, recalibrated


def _require_common_temporal_eligibility_cohort(
    static_scores: FederatedScoreArtifactManifest,
    future_scores: FederatedScoreArtifactManifest,
) -> None:
    static_clients = frozenset(
        item.client for item in eligible_calibration_scores(static_scores, PartitionRole.CALIBRATION)
    )
    frozen_clients = frozenset(
        item.client for item in eligible_calibration_scores(future_scores, PartitionRole.CALIBRATION)
    )
    recalibrated_clients = frozenset(
        item.client for item in eligible_calibration_scores(future_scores, PartitionRole.FUTURE_RECALIBRATION)
    )
    if static_clients != frozen_clients or frozen_clients != recalibrated_clients:
        raise ScientificContractError(
            ErrorMessage("temporal state comparisons require one identical calibration-eligible client cohort"),
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )


def _require_matching_temporal_evaluation_cohorts(
    static: TemporalStateResult,
    frozen: TemporalStateResult,
    recalibrated: TemporalStateResult,
    methods: tuple[FederatedThresholdMethod, ...],
) -> None:
    for method in methods:
        outcomes = (
            static.outcome_for(method),
            frozen.outcome_for(method),
            recalibrated.outcome_for(method),
        )
        cohorts = tuple(
            tuple(client.client for client in outcome.clients if client.cohort is EvaluationCohort.FPR_EVALUABLE)
            for outcome in outcomes
        )
        if cohorts[0] != cohorts[1] or cohorts[1] != cohorts[2]:
            raise ScientificContractError(
                ErrorMessage("temporal recovery requires identical FPR-evaluable client cohorts across all states"),
                subject=method,
            )


def _cluster_aggregation(method: FederatedThresholdMethod) -> ClusterThresholdAggregation | None:
    if method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
        return ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
    return None


def _evaluate_state(
    *,
    context: FederatedExecutionContext,
    method_coordinates: tuple[ExperimentCoordinate, ...],
    identity: ExternalTemporalExecutionIdentity,
    scores: FederatedScoreArtifactManifest,
    calibration_role: PartitionRole,
    threshold_methods: tuple[FederatedThresholdMethod, ...],
    provenance: TemporalDeploymentProvenance,
    output_root: Path,
    overwrite: bool,
) -> TemporalStateResult:
    eligible = eligible_calibration_scores(scores, calibration_role)
    capabilities = population_capabilities(context.coordinate.population)
    reference_evidence = None
    completed: list[FederatedThresholdMethod] = []
    outcomes: list[TemporalMethodOutcome] = []
    unavailable: list[TemporalMethodUnavailability] = []
    state_root = bounded_evidence_seed_directory(identity, context.coordinate.training_seed, output_root)
    for method in threshold_methods:
        execution_coordinate = _method_coordinate(method_coordinates, method)
        threshold_publication = construct_and_publish_federated_thresholds(
            FederatedThresholdConstructionRequest(
                request=ThresholdConstructionRequest(
                    method=method,
                    coordinate=context.coordinate,
                    quantile=CANONICAL_QUANTILE,
                    capabilities=capabilities,
                    eligible=eligible,
                    family_by_client=context.family_by_client,
                    support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                    cluster_threshold_aggregation=_cluster_aggregation(method),
                ),
                output_directory=state_root / TemporalArtifactDirectory.THRESHOLDS.value / method.value,
                overwrite=overwrite,
                temporal_provenance=provenance,
                temporal_score_manifest=scores,
            )
        )
        threshold = threshold_publication.result
        if isinstance(threshold, ThresholdUnavailableResult):
            unavailable.append(
                TemporalMethodUnavailability(
                    method=method,
                    reason=threshold.reason,
                    detail=AnalysisReasonText(threshold.detail),
                )
            )
            continue
        evaluation_inputs = build_federated_evaluation_inputs(scores, method, calibration_role=calibration_role)
        evaluation = evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                execution_coordinate=execution_coordinate,
                score_manifest=scores,
                threshold_result=threshold,
                cohort=evaluation_inputs.cohort,
                fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
                evidence_role=identity.evidence_role,
                calibration_scores=eligible,
                target_quantile=CANONICAL_QUANTILE,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=identity,
                temporal_provenance=provenance,
                temporal_threshold_provenance=provenance,
                output_directory=state_root / TemporalArtifactDirectory.EVALUATIONS.value / method.value,
                overwrite=overwrite,
            )
        )
        cv_fpr = metric_by_id(evaluation.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        if cv_fpr.status is not MetricStatus.AVAILABLE or cv_fpr.value is None:
            raise ScientificContractError(
                ErrorMessage("temporal evaluation requires available population CV(FPR)"), subject=method
            )
        mean_metric = metric_by_id(evaluation.population.metrics, MetricId.MEAN_FPR)
        mean_fpr = mean_metric.value if mean_metric.status is MetricStatus.AVAILABLE else None
        if not evaluation.clients:
            raise ScientificContractError(
                ErrorMessage("temporal evaluation requires non-empty client metrics"), subject=method
            )
        if reference_evidence is None:
            reference_evidence = evaluation_inputs.fixed_score_evidence
        unavailable_reasons = _cohort_unavailable_reasons(evaluation_inputs.cohort)
        completed.append(method)
        outcomes.append(
            TemporalMethodOutcome(
                method=method,
                fpr_coefficient_of_variation=cv_fpr.value,
                mean_fpr=mean_fpr,
                clients=evaluation.clients,
                excluded_clients=evaluation.population.excluded_clients,
                unavailable_reasons=unavailable_reasons,
            )
        )
    if not completed:
        raise ScientificContractError(
            ErrorMessage("temporal execution produced no evaluable threshold method"), subject=identity.temporal_state
        )
    if identity.temporal_state is None:
        raise ScientificContractError(ErrorMessage("temporal result requires an explicit state"))
    return TemporalStateResult(
        state=identity.temporal_state,
        completed_threshold_methods=tuple(completed),
        provenance=provenance,
        outcomes=tuple(outcomes),
        unavailable_methods=tuple(unavailable),
    )


def _publish_temporal_method_campaign(
    *,
    method: FederatedThresholdMethod,
    campaign: TemporalCampaignResult,
    declaration: ExperimentDeclaration,
    output_root: Path,
    overwrite: bool,
) -> TemporalMethodCampaignAnalysis:
    records = tuple(seed.recovery_for(method) for seed in campaign.seeds)
    static_provenance, frozen_provenance, recalibrated_provenance = _document_level_deployment_provenance(records)
    output_directory = _temporal_campaign_analysis_directory(method, output_root)
    if overwrite and output_directory.exists():
        rmtree(output_directory)
    analysis = analyze_temporal_evidence(
        AnalyzeTemporalEvidenceRequest(
            experiment=declaration.id,
            threshold_method=method,
            static_reference_identity=_declaration_identity(declaration, TemporalState.STATIC_REFERENCE),
            frozen_identity=_declaration_identity(declaration, TemporalState.FROZEN_FUTURE),
            recalibrated_identity=_declaration_identity(declaration, TemporalState.RECALIBRATED_FUTURE),
            static_reference_provenance=static_provenance,
            frozen_provenance=frozen_provenance,
            recalibrated_provenance=recalibrated_provenance,
            records=records,
            output_directory=output_directory,
        )
    )
    export_temporal_publication(analysis.document, output_directory)
    return TemporalMethodCampaignAnalysis(
        method=method,
        output_directory=output_directory,
    )


def _validate_shared_temporal_detector(
    static: TemporalDeploymentProvenance, frozen: TemporalDeploymentProvenance
) -> None:
    if static.coordinate != frozen.coordinate:
        raise ScientificContractError(
            ErrorMessage(
                "static reference and future states must share one historical detector and preprocessing state"
            ),
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )


def _validate_campaign_recovery_provenance(campaign: TemporalCampaignResult) -> None:
    for seed_result in campaign.seeds:
        for item in seed_result.recoveries:
            provenance = item.recovery.provenance
            if provenance.seed != seed_result.partition_seed:
                raise ScientificContractError(ErrorMessage("temporal provenance seed mismatch"), subject=item.method)
            if provenance.experiment is not item.recovery.experiment:
                raise ScientificContractError(
                    ErrorMessage("temporal provenance experiment mismatch"), subject=item.method
                )
            if provenance.threshold_method is not item.method:
                raise ScientificContractError(
                    ErrorMessage("temporal provenance threshold-method mismatch"), subject=item.method
                )
            if not item.recovery.client_trajectories:
                raise ScientificContractError(
                    ErrorMessage("temporal recovery requires client trajectories"), subject=item.method
                )


def _validate_campaign_shared_detector_identity(campaign: TemporalCampaignResult) -> None:
    for seed in campaign.seeds:
        _validate_shared_temporal_detector(seed.static_reference.provenance, seed.frozen_future.provenance)
        validate_frozen_recalibrated_pair(seed.frozen_future.provenance, seed.recalibrated_future.provenance)


def _document_level_deployment_provenance(
    records: tuple[TemporalRecoveryResult, ...],
) -> tuple[TemporalDeploymentProvenance, TemporalDeploymentProvenance, TemporalDeploymentProvenance]:
    if not records:
        raise ScientificContractError(ErrorMessage("temporal document provenance requires recovery records"))
    for record in records:
        _validate_shared_temporal_detector(record.provenance.static_reference, record.provenance.frozen_future)
        validate_frozen_recalibrated_pair(record.provenance.frozen_future, record.provenance.recalibrated_future)
    static_template = records[0].provenance.static_reference
    frozen_template = records[0].provenance.frozen_future
    recalibrated_template = records[0].provenance.recalibrated_future
    static = TemporalDeploymentProvenance(
        state=TemporalState.STATIC_REFERENCE,
        split_protocol=static_template.split_protocol,
        calibration_role=static_template.calibration_role,
        evaluation_role=static_template.evaluation_role,
        coordinate=tuple(
            coordinate
            for item in records
            for coordinate in training_coordinates(item.provenance.static_reference.coordinate)
        ),
        calibration_records=tuple(
            record for item in records for record in item.provenance.static_reference.calibration_records
        ),
        evaluation_records=tuple(
            record for item in records for record in item.provenance.static_reference.evaluation_records
        ),
    )
    frozen = TemporalDeploymentProvenance(
        state=TemporalState.FROZEN_FUTURE,
        split_protocol=frozen_template.split_protocol,
        calibration_role=frozen_template.calibration_role,
        evaluation_role=frozen_template.evaluation_role,
        coordinate=tuple(
            coordinate
            for item in records
            for coordinate in training_coordinates(item.provenance.frozen_future.coordinate)
        ),
        calibration_records=tuple(
            record for item in records for record in item.provenance.frozen_future.calibration_records
        ),
        evaluation_records=tuple(
            record for item in records for record in item.provenance.frozen_future.evaluation_records
        ),
    )
    recalibrated = TemporalDeploymentProvenance(
        state=TemporalState.RECALIBRATED_FUTURE,
        split_protocol=recalibrated_template.split_protocol,
        calibration_role=recalibrated_template.calibration_role,
        evaluation_role=recalibrated_template.evaluation_role,
        coordinate=frozen.coordinate,
        calibration_records=tuple(
            record for item in records for record in item.provenance.recalibrated_future.calibration_records
        ),
        evaluation_records=frozen.evaluation_records,
    )
    validate_frozen_recalibrated_pair(frozen, recalibrated)
    _validate_shared_temporal_detector(static, frozen)
    return static, frozen, recalibrated


def _build_client_trajectories(
    *,
    seed: Seed,
    method: FederatedThresholdMethod,
    static_outcome: TemporalMethodOutcome,
    frozen_outcome: TemporalMethodOutcome,
    recalibrated_outcome: TemporalMethodOutcome,
    static_calibration_records: tuple[FederatedScoreRecord, ...],
    future_recalibration_records: tuple[FederatedScoreRecord, ...],
) -> tuple[TemporalClientTrajectory, ...]:
    clients = tuple(
        sorted(
            frozenset(item.client for item in static_outcome.clients)
            | frozenset(item.client for item in frozen_outcome.clients)
            | frozenset(item.client for item in recalibrated_outcome.clients)
        )
    )
    trajectories: list[TemporalClientTrajectory] = []
    for client in clients:
        static_client = _client_by_identity(static_outcome.clients, client)
        frozen_client = _client_by_identity(frozen_outcome.clients, client)
        recalibrated_client = _client_by_identity(recalibrated_outcome.clients, client)
        eligible = _client_is_eligible(static_client, frozen_client, recalibrated_client)
        trajectories.append(
            TemporalClientTrajectory(
                seed=seed,
                client=client,
                threshold_method=method,
                eligible=eligible,
                exclusion_reason=None
                if eligible
                else AnalysisReasonText(
                    _exclusion_reason(client, static_outcome, frozen_outcome, recalibrated_outcome)
                ),
                threshold_static=_client_threshold(static_client),
                threshold_frozen=_client_threshold(frozen_client),
                threshold_recalibrated=_client_threshold(recalibrated_client),
                fpr_static=_client_metric(static_client, MetricId.FALSE_POSITIVE_RATE),
                fpr_frozen=_client_metric(frozen_client, MetricId.FALSE_POSITIVE_RATE),
                fpr_recalibrated=_client_metric(recalibrated_client, MetricId.FALSE_POSITIVE_RATE),
                tpr_static=_client_metric(static_client, MetricId.TRUE_POSITIVE_RATE),
                tpr_frozen=_client_metric(frozen_client, MetricId.TRUE_POSITIVE_RATE),
                tpr_recalibrated=_client_metric(recalibrated_client, MetricId.TRUE_POSITIVE_RATE),
                balanced_accuracy_static=_client_metric(static_client, MetricId.BALANCED_ACCURACY),
                balanced_accuracy_frozen=_client_metric(frozen_client, MetricId.BALANCED_ACCURACY),
                balanced_accuracy_recalibrated=_client_metric(recalibrated_client, MetricId.BALANCED_ACCURACY),
                macro_f1_static=_client_metric(static_client, MetricId.BINARY_MACRO_F1),
                macro_f1_frozen=_client_metric(frozen_client, MetricId.BINARY_MACRO_F1),
                macro_f1_recalibrated=_client_metric(recalibrated_client, MetricId.BINARY_MACRO_F1),
                drift_js=_client_drift_js(client, static_calibration_records, future_recalibration_records),
            )
        )
    return tuple(trajectories)


def _client_drift_js(
    client: ClientIdentity,
    static_records: tuple[FederatedScoreRecord, ...],
    future_records: tuple[FederatedScoreRecord, ...],
) -> MetricValue | None:
    historical = next((record for record in static_records if record.scored_client == client), None)
    future = next((record for record in future_records if record.scored_client == client), None)
    return None if historical is None or future is None else temporal_drift_js(historical, future)


def _client_by_identity(clients: tuple[ClientMetricResult, ...], identity: ClientIdentity) -> ClientMetricResult | None:
    return next((client for client in clients if client.client == identity), None)


def _exclusion_reason(
    client: ClientIdentity,
    *outcomes: TemporalMethodOutcome,
) -> TemporalClientUnavailableReason:
    excluded = any(excluded_client == client for outcome in outcomes for excluded_client in outcome.excluded_clients)
    return (
        TemporalClientUnavailableReason.EXCLUDED_FROM_FPR_EVALUABLE_COHORT
        if excluded
        else TemporalClientUnavailableReason.CLIENT_NOT_EVALUABLE
    )


def _client_is_eligible(
    static_client: ClientMetricResult | None,
    frozen_client: ClientMetricResult | None,
    recalibrated_client: ClientMetricResult | None,
) -> bool:
    if static_client is None or frozen_client is None or recalibrated_client is None:
        return False
    return all(
        client.cohort is EvaluationCohort.FPR_EVALUABLE
        for client in (static_client, frozen_client, recalibrated_client)
    )


def _client_threshold(client: ClientMetricResult | None) -> MetricValue | None:
    return None if client is None else MetricValue(client.threshold.value)


def _client_metric(client: ClientMetricResult | None, metric: MetricId) -> MetricValue | None:
    if client is None:
        return None
    return metric_value(metric_by_id(client.metrics, metric))


def _cohort_unavailable_reasons(cohort: EvaluationCohortManifest) -> tuple[AnalysisReasonText, ...]:
    reasons: list[AnalysisReasonText] = []
    for record in sorted(cohort.records, key=lambda item: item.client.client_id.value):
        if record.fpr_evaluable:
            continue
        client_id = record.client.client_id
        if record.exclusion_reasons:
            reasons.extend(AnalysisReasonText(f"{client_id}:{reason.value}") for reason in record.exclusion_reasons)
        else:
            reasons.append(
                AnalysisReasonText(f"{client_id.value}:{TemporalClientUnavailableReason.NOT_FPR_EVALUABLE.value}")
            )
    return tuple(reasons)


def _union_clients(*groups: tuple[ClientIdentity, ...]) -> tuple[ClientIdentity, ...]:
    return tuple(sorted(frozenset(client for group in groups for client in group)))


def _union_text(
    *groups: tuple[AnalysisReasonText, ...],
) -> tuple[AnalysisReasonText, ...]:
    ordered: list[AnalysisReasonText] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
    return tuple(ordered)


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
            ErrorMessage("all temporal states must complete the same declared threshold methods"),
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )
    return static.completed_threshold_methods


def _execution_identity(coordinate: ExperimentCoordinate) -> ExternalTemporalExecutionIdentity:
    if coordinate.temporal_state is None:
        raise ScientificContractError(ErrorMessage("temporal execution requires a temporal state"))
    return ExternalTemporalExecutionIdentity(
        experiment=coordinate.experiment,
        population=coordinate.population,
        evidence_role=coordinate.evidence_role,
        temporal_state=coordinate.temporal_state,
    )


def _declaration_identity(
    declaration: ExperimentDeclaration, state: TemporalState
) -> ExternalTemporalExecutionIdentity:
    return ExternalTemporalExecutionIdentity(
        experiment=declaration.id,
        population=declaration.population,
        evidence_role=declaration.role,
        temporal_state=state,
    )


def _temporal_coordinates(partition_seed: Seed, declaration: ExperimentDeclaration) -> TemporalCoordinateSet:
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(partition_seed,)))
    static_reference_methods = _coordinates_for_state(plan, TemporalState.STATIC_REFERENCE)
    frozen_future_methods = _coordinates_for_state(plan, TemporalState.FROZEN_FUTURE)
    recalibrated_future_methods = _coordinates_for_state(plan, TemporalState.RECALIBRATED_FUTURE)
    return TemporalCoordinateSet(
        static_reference=static_reference_methods[0],
        frozen_future=frozen_future_methods[0],
        recalibrated_future=recalibrated_future_methods[0],
        static_reference_methods=static_reference_methods,
        frozen_future_methods=frozen_future_methods,
        recalibrated_future_methods=recalibrated_future_methods,
    )


def _coordinates_for_state(plan: ExperimentPlan, state: TemporalState) -> tuple[ExperimentCoordinate, ...]:
    matches = tuple(entry.coordinate for entry in plan.entries if entry.coordinate.temporal_state is state)
    if not matches:
        raise ScientificContractError(ErrorMessage(f"no temporal coordinate is declared for {state.value}"))
    by_method = tuple(
        next(coordinate for coordinate in matches if coordinate.threshold_method is method)
        for method in sorted({coordinate.threshold_method for coordinate in matches}, key=lambda method: method.value)
    )
    if len(by_method) != len({coordinate.threshold_method for coordinate in matches}):
        raise ScientificContractError(
            ErrorMessage(f"temporal state has duplicate method coordinates for {state.value}")
        )
    first = matches[0]
    if any(
        candidate.dataset is not first.dataset
        or candidate.population is not first.population
        or candidate.split_protocol is not first.split_protocol
        or candidate.preprocessing_protocol is not first.preprocessing_protocol
        or candidate.training_model is not first.training_model
        for candidate in matches[1:]
    ):
        raise ScientificContractError(
            ErrorMessage(f"temporal coordinates disagree on detector identity for {state.value}")
        )
    return by_method


def _method_coordinate(
    coordinates: tuple[ExperimentCoordinate, ...], method: FederatedThresholdMethod
) -> ExperimentCoordinate:
    matches = tuple(coordinate for coordinate in coordinates if coordinate.threshold_method is method)
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(f"temporal execution requires exactly one coordinate for {method.value}"), subject=method
        )
    return matches[0]


def _temporal_campaign_analysis_directory(method: FederatedThresholdMethod, output_root: Path) -> Path:
    declaration = _temporal_declaration()
    return (
        output_root
        / ExecutionRootDirectory.BOUNDED_EVIDENCE.value
        / declaration.id.value
        / declaration.population.value
        / declaration.role.value
        / TemporalArtifactDirectory.ANALYSIS.value
        / method.value
    )


def _temporal_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage("the temporal experiment must be declared exactly once"))
    return matches[0]
