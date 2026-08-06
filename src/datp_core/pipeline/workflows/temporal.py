"""One-shot temporal reference, future recalibration, and analysis execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.analysis.temporal import (
    TemporalClientTrajectory,
    TemporalRecoveryResult,
    TemporalSeedProvenance,
    temporal_recovery,
)
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.datasets.registry import population_capabilities
from datp_core.domain.enums import (
    EvaluationCohort,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.fixed_score.construction import build_federated_evaluation_inputs
from datp_core.evaluation.models import ClientMetricResult, MetricStatus, metric_by_id
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.decision.evidence import AnalyzeTemporalEvidenceRequest, analyze_temporal_evidence
from datp_core.pipeline.decision.federated import (
    ConstructFederatedThresholdsRequest,
    EvaluateFederatedDetectorRequest,
    construct_federated_thresholds,
    evaluate_federated_detector,
)
from datp_core.pipeline.execution.checkpoints import select_execution_checkpoint
from datp_core.pipeline.execution.context import (
    FederatedExecutionContext,
    client_scoring_inputs,
    resolve_execution_context,
    training_autoencoder,
    training_feature_names,
)
from datp_core.pipeline.execution.evidence import eligible_calibration_scores
from datp_core.pipeline.execution.layout import (
    ExecutionArtifactDirectory,
    ExecutionRootDirectory,
    bounded_evidence_seed_directory,
)
from datp_core.pipeline.execution.matched_reference import matched_static_reference_inputs
from datp_core.pipeline.execution.score_generation import score_selected_checkpoint
from datp_core.pipeline.planning import ExperimentPlan, expand_experiment_plan
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration, ExternalTemporalExecutionIdentity
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, SeedCohort
from datp_core.protocols.temporal import TemporalDeploymentProvenance, validate_frozen_recalibrated_pair
from datp_core.reporting.export import export_temporal_publication
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.publication import threshold_result_checksum


class TemporalArtifactDirectory(StrEnum):
    SCORES = "scores"
    THRESHOLDS = "thresholds"
    EVALUATIONS = "evaluations"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodOutcome:
    method: FederatedThresholdMethod
    fpr_coefficient_of_variation: MetricValue
    mean_fpr: MetricValue | None
    threshold_checksum: Checksum
    evaluation_checksum: Checksum
    client_inventory_checksum: Checksum
    eligibility_checksum: Checksum
    source_row_checksum: Checksum
    row_order_checksum: Checksum
    clients: tuple[ClientMetricResult, ...]
    excluded_clients: tuple[ClientIdentity, ...]
    exclusions: tuple[str, ...]
    unavailable_reasons: tuple[str, ...]


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
class TemporalMethodRecovery:
    method: FederatedThresholdMethod
    recovery: TemporalRecoveryResult


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalMethodCampaignAnalysis:
    method: FederatedThresholdMethod
    complete_digest: Checksum
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
        if tuple(item.method for item in self.recoveries) != methods:
            raise ValueError("temporal recoveries must follow the completed threshold-method order")
        if any(item.recovery.seed != self.partition_seed for item in self.recoveries):
            raise ValueError("temporal recovery records must match their partition seed")

    def recovery_for(self, method: FederatedThresholdMethod) -> TemporalRecoveryResult:
        matches = tuple(item.recovery for item in self.recoveries if item.method is method)
        if len(matches) != 1:
            raise ScientificContractError("temporal seed must contain exactly one recovery per method", subject=method)
        return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalCampaignResult:
    seeds: tuple[TemporalSeedResult, ...]
    analyses: tuple[TemporalMethodCampaignAnalysis, ...] = ()

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

    def for_state(self, state: TemporalState) -> ExperimentCoordinate:
        match state:
            case TemporalState.STATIC_REFERENCE:
                return self.static_reference
            case TemporalState.FROZEN_FUTURE:
                return self.frozen_future
            case TemporalState.RECALIBRATED_FUTURE:
                return self.recalibrated_future


def run_temporal_campaign() -> TemporalCampaignResult:
    seeds = tuple(run_temporal_seed(seed) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values)
    campaign = TemporalCampaignResult(seeds=seeds)
    analyses = analyze_temporal_campaign(campaign)
    return TemporalCampaignResult(seeds=seeds, analyses=analyses)


def run_temporal_seed(partition_seed: Seed) -> TemporalSeedResult:
    declaration = _temporal_declaration()
    coordinates = _temporal_coordinates(partition_seed, declaration)
    static, frozen, recalibrated = _execute_temporal_states(declaration, coordinates)
    methods = _common_completed_methods(static, frozen, recalibrated)
    recoveries = tuple(
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
    )
    return TemporalSeedResult(
        partition_seed=partition_seed,
        static_reference=static,
        frozen_future=frozen,
        recalibrated_future=recalibrated,
        recoveries=recoveries,
    )


def analyze_temporal_campaign(campaign: TemporalCampaignResult) -> tuple[TemporalMethodCampaignAnalysis, ...]:
    if not campaign.seeds:
        raise ScientificContractError("temporal campaign analysis requires completed seed results")
    methods = tuple(item.method for item in campaign.seeds[0].recoveries)
    declaration = _temporal_declaration()
    _validate_campaign_recovery_provenance(campaign)
    _validate_campaign_shared_detector_identity(campaign)
    return tuple(
        _publish_temporal_method_campaign(
            method=method,
            campaign=campaign,
            declaration=declaration,
        )
        for method in methods
    )


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
    )
    if not trajectories:
        raise ScientificContractError(
            "temporal recovery requires non-empty client trajectories when evaluations exist",
            subject=method,
            reason=f"seed={partition_seed.value}",
        )
    provenance = TemporalSeedProvenance(
        seed=partition_seed,
        experiment=declaration.id,
        population=declaration.population.value,
        threshold_method=method,
        static_reference=static.provenance,
        frozen_future=frozen.provenance,
        recalibrated_future=recalibrated.provenance,
        static_threshold_checksum=static_outcome.threshold_checksum,
        frozen_threshold_checksum=frozen_outcome.threshold_checksum,
        recalibrated_threshold_checksum=recalibrated_outcome.threshold_checksum,
        static_evaluation_checksum=static_outcome.evaluation_checksum,
        frozen_evaluation_checksum=frozen_outcome.evaluation_checksum,
        recalibrated_evaluation_checksum=recalibrated_outcome.evaluation_checksum,
        client_inventory_checksum=frozen_outcome.client_inventory_checksum,
        eligibility_checksum=frozen_outcome.eligibility_checksum,
        source_row_checksum=frozen_outcome.source_row_checksum,
        row_order_checksum=frozen_outcome.row_order_checksum,
        exclusions=_union_text(static_outcome.exclusions, frozen_outcome.exclusions, recalibrated_outcome.exclusions),
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
        mean_fpr_static=static_outcome.mean_fpr,
        mean_fpr_frozen=frozen_outcome.mean_fpr,
        mean_fpr_recalibrated=recalibrated_outcome.mean_fpr,
        provenance=provenance,
        client_trajectories=trajectories,
    )


def _execute_temporal_states(
    declaration: ExperimentDeclaration,
    coordinates: TemporalCoordinateSet,
) -> tuple[TemporalStateResult, TemporalStateResult, TemporalStateResult]:
    frozen_coordinate = coordinates.frozen_future
    context = resolve_execution_context(frozen_coordinate, OUTPUTS_ROOT)
    autoencoder = training_autoencoder(frozen_coordinate.dataset)
    feature_names = training_feature_names(frozen_coordinate.dataset)
    checkpoint = select_execution_checkpoint(context, autoencoder=autoencoder, feature_names=feature_names)
    future_scores = score_selected_checkpoint(
        checkpoint=checkpoint,
        scored_split_protocol=frozen_coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=client_scoring_inputs(context.preprocessing.client_publications, context.clients),
        output_directory=context.training_directory / ExecutionArtifactDirectory.SCORES,
        preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
        split_manifest_checksum=context.split_manifest_checksum,
    )
    static_inputs = matched_static_reference_inputs(context, OUTPUTS_ROOT)
    static_coordinate = coordinates.static_reference
    static_identity = _execution_identity(static_coordinate)
    static_root = bounded_evidence_seed_directory(static_identity, static_coordinate.training_seed, OUTPUTS_ROOT)
    static_scores = score_selected_checkpoint(
        checkpoint=checkpoint,
        scored_split_protocol=static_coordinate.split_protocol,
        autoencoder=autoencoder,
        feature_names=feature_names,
        clients=static_inputs.clients,
        output_directory=static_root / TemporalArtifactDirectory.SCORES,
        preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
        split_manifest_checksum=static_inputs.split_manifest_checksum,
    )
    static_provenance = TemporalDeploymentProvenance.from_score_manifest(TemporalState.STATIC_REFERENCE, static_scores)
    frozen_provenance = TemporalDeploymentProvenance.from_score_manifest(TemporalState.FROZEN_FUTURE, future_scores)
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
    )
    frozen = _evaluate_state(
        context=context,
        identity=_execution_identity(frozen_coordinate),
        scores=future_scores,
        calibration_role=PartitionRole.CALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=frozen_provenance,
    )
    recalibrated = _evaluate_state(
        context=context,
        identity=_execution_identity(coordinates.recalibrated_future),
        scores=future_scores,
        calibration_role=PartitionRole.FUTURE_RECALIBRATION,
        threshold_methods=declaration.federated_thresholds,
        provenance=recalibrated_provenance,
    )
    return static, frozen, recalibrated


def _evaluate_state(
    *,
    context: FederatedExecutionContext,
    identity: ExternalTemporalExecutionIdentity,
    scores: FederatedScoreArtifactManifest,
    calibration_role: PartitionRole,
    threshold_methods: tuple[FederatedThresholdMethod, ...],
    provenance: TemporalDeploymentProvenance,
) -> TemporalStateResult:
    eligible = eligible_calibration_scores(scores, calibration_role)
    capabilities = population_capabilities(context.coordinate.population)
    reference_evidence = None
    completed: list[FederatedThresholdMethod] = []
    outcomes: list[TemporalMethodOutcome] = []
    output_root = bounded_evidence_seed_directory(identity, context.coordinate.training_seed, OUTPUTS_ROOT)
    for method in threshold_methods:
        threshold_publication = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    method=method,
                    coordinate=context.coordinate,
                    quantile=CANONICAL_QUANTILE,
                    capabilities=capabilities,
                    eligible=eligible,
                    family_by_client=context.family_by_client,
                ),
                output_directory=output_root / TemporalArtifactDirectory.THRESHOLDS / method.value,
                overwrite=False,
                temporal_provenance=provenance,
                temporal_score_manifest=scores,
            )
        )
        threshold = threshold_publication.result
        if isinstance(threshold, ThresholdUnavailableResult):
            continue
        evaluation_inputs = build_federated_evaluation_inputs(scores, method, calibration_role=calibration_role)
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
                output_directory=output_root / TemporalArtifactDirectory.EVALUATIONS / method.value,
                overwrite=False,
            )
        )
        result = metric_by_id(evaluation.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        if result.status is not MetricStatus.AVAILABLE or result.value is None:
            raise ScientificContractError(
                "temporal evaluation requires available population CV(FPR)",
                subject=method,
            )
        mean_fpr_metric = metric_by_id(evaluation.population.metrics, MetricId.MEAN_FPR)
        mean_fpr = (
            mean_fpr_metric.value
            if mean_fpr_metric.status is MetricStatus.AVAILABLE and mean_fpr_metric.value is not None
            else None
        )
        if not evaluation.clients:
            raise ScientificContractError(
                "temporal evaluation requires non-empty client metrics for trajectory construction",
                subject=method,
            )
        if reference_evidence is None:
            reference_evidence = evaluation_inputs.fixed_score_evidence
        evidence = evaluation_inputs.fixed_score_evidence
        exclusions, unavailable_reasons = _cohort_exclusion_records(evaluation_inputs.cohort)
        completed.append(method)
        outcomes.append(
            TemporalMethodOutcome(
                method=method,
                fpr_coefficient_of_variation=result.value,
                mean_fpr=mean_fpr,
                threshold_checksum=threshold_result_checksum(threshold),
                evaluation_checksum=evaluation.complete_digest,
                client_inventory_checksum=evidence.population.client_inventory_checksum,
                eligibility_checksum=evidence.population.eligibility_cohort_checksum,
                source_row_checksum=evidence.evaluation.source_row_checksum,
                row_order_checksum=evidence.evaluation.score_order_checksum,
                clients=evaluation.clients,
                excluded_clients=evaluation.population.excluded_clients,
                exclusions=exclusions,
                unavailable_reasons=unavailable_reasons,
            )
        )
    if not completed:
        raise ScientificContractError(
            "temporal execution produced no evaluable threshold method",
            subject=identity.temporal_state,
        )
    if identity.temporal_state is None:
        raise ScientificContractError("temporal result requires an explicit state")
    return TemporalStateResult(
        state=identity.temporal_state,
        completed_threshold_methods=tuple(completed),
        provenance=provenance,
        outcomes=tuple(outcomes),
    )


def _publish_temporal_method_campaign(
    *,
    method: FederatedThresholdMethod,
    campaign: TemporalCampaignResult,
    declaration: ExperimentDeclaration,
) -> TemporalMethodCampaignAnalysis:
    records = tuple(seed.recovery_for(method) for seed in campaign.seeds)
    static_provenance, frozen_provenance, recalibrated_provenance = _document_level_deployment_provenance(records)
    output_directory = _temporal_campaign_analysis_directory(method)
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
            overwrite=False,
        )
    )
    export_temporal_publication(analysis.document, output_directory)
    return TemporalMethodCampaignAnalysis(
        method=method,
        complete_digest=analysis.complete_digest,
        output_directory=output_directory,
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


def _validate_campaign_recovery_provenance(campaign: TemporalCampaignResult) -> None:
    for seed_result in campaign.seeds:
        for item in seed_result.recoveries:
            provenance = item.recovery.provenance
            if provenance.seed != seed_result.partition_seed:
                raise ScientificContractError(
                    "temporal provenance seed must match the recovery seed",
                    subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
                    reason=f"seed={seed_result.partition_seed.value}",
                )
            if provenance.experiment is not item.recovery.experiment:
                raise ScientificContractError(
                    "temporal provenance experiment must match the recovery experiment",
                    subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
                    reason=f"seed={seed_result.partition_seed.value}",
                )
            if provenance.threshold_method is not item.method:
                raise ScientificContractError(
                    "temporal provenance threshold method must match the recovery method",
                    subject=item.method,
                    reason=f"seed={seed_result.partition_seed.value}",
                )
            if not item.recovery.client_trajectories:
                raise ScientificContractError(
                    "temporal campaign recovery records require non-empty client trajectories",
                    subject=item.method,
                    reason=f"seed={seed_result.partition_seed.value}",
                )


def _validate_campaign_shared_detector_identity(campaign: TemporalCampaignResult) -> None:
    detector_keys = tuple(
        (
            seed.static_reference.provenance.checkpoint_checksum,
            seed.static_reference.provenance.preprocessing_state_set_checksum,
            seed.frozen_future.provenance.checkpoint_checksum,
            seed.frozen_future.provenance.preprocessing_state_set_checksum,
            seed.recalibrated_future.provenance.checkpoint_checksum,
            seed.recalibrated_future.provenance.preprocessing_state_set_checksum,
        )
        for seed in campaign.seeds
    )
    if len(frozenset(detector_keys)) != 1:
        raise ScientificContractError(
            "temporal campaign seeds must share one fitted detector and preprocessing identity",
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )
    for seed in campaign.seeds:
        _validate_shared_temporal_detector(seed.static_reference.provenance, seed.frozen_future.provenance)
        validate_frozen_recalibrated_pair(seed.frozen_future.provenance, seed.recalibrated_future.provenance)


def _document_level_deployment_provenance(
    records: tuple[TemporalRecoveryResult, ...],
) -> tuple[TemporalDeploymentProvenance, TemporalDeploymentProvenance, TemporalDeploymentProvenance]:
    """Bind document-level detector identity after multi-seed agreement.

    Score-level bindings remain authoritative only on each seed's recovery provenance.
    Document-level fields used for detector sharing are verified equal across seeds;
    score checksums are not taken from an arbitrary seed as campaign-wide identity.
    """
    if not records:
        raise ScientificContractError("temporal document provenance requires recovery records")
    detector_keys = tuple(
        (
            record.provenance.static_reference.checkpoint_checksum,
            record.provenance.static_reference.preprocessing_state_set_checksum,
            record.provenance.static_reference.coordinate_checksum,
            record.provenance.frozen_future.checkpoint_checksum,
            record.provenance.frozen_future.preprocessing_state_set_checksum,
            record.provenance.frozen_future.coordinate_checksum,
            record.provenance.recalibrated_future.checkpoint_checksum,
            record.provenance.recalibrated_future.preprocessing_state_set_checksum,
            record.provenance.recalibrated_future.coordinate_checksum,
        )
        for record in records
    )
    if len(frozenset(detector_keys)) != 1:
        raise ScientificContractError(
            "temporal document provenance requires shared detector identity across seeds",
            subject=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        )
    for record in records:
        _validate_shared_temporal_detector(
            record.provenance.static_reference,
            record.provenance.frozen_future,
        )
        validate_frozen_recalibrated_pair(
            record.provenance.frozen_future,
            record.provenance.recalibrated_future,
        )
    # Shared detector identity is verified above. Document-level TemporalDeploymentProvenance
    # still needs a concrete binding triple for API validation; use the verified shared
    # detector fields with seed-invariant partition roles/protocols, and aggregate
    # seed-varying score checksums so no single seed is silently treated as campaign identity.
    static_template = records[0].provenance.static_reference
    frozen_template = records[0].provenance.frozen_future
    recalibrated_template = records[0].provenance.recalibrated_future
    static = TemporalDeploymentProvenance(
        state=TemporalState.STATIC_REFERENCE,
        split_protocol=static_template.split_protocol,
        calibration_role=static_template.calibration_role,
        evaluation_role=static_template.evaluation_role,
        coordinate_checksum=static_template.coordinate_checksum,
        checkpoint_checksum=static_template.checkpoint_checksum,
        preprocessing_state_set_checksum=static_template.preprocessing_state_set_checksum,
        split_manifest_checksum=_aggregate_checksums(
            tuple(item.provenance.static_reference.split_manifest_checksum for item in records)
        ),
        calibration_score_set_checksum=_aggregate_checksums(
            tuple(item.provenance.static_reference.calibration_score_set_checksum for item in records)
        ),
        evaluation_score_set_checksum=_aggregate_checksums(
            tuple(item.provenance.static_reference.evaluation_score_set_checksum for item in records)
        ),
    )
    frozen = TemporalDeploymentProvenance(
        state=TemporalState.FROZEN_FUTURE,
        split_protocol=frozen_template.split_protocol,
        calibration_role=frozen_template.calibration_role,
        evaluation_role=frozen_template.evaluation_role,
        coordinate_checksum=frozen_template.coordinate_checksum,
        checkpoint_checksum=frozen_template.checkpoint_checksum,
        preprocessing_state_set_checksum=frozen_template.preprocessing_state_set_checksum,
        split_manifest_checksum=_aggregate_checksums(
            tuple(item.provenance.frozen_future.split_manifest_checksum for item in records)
        ),
        calibration_score_set_checksum=_aggregate_checksums(
            tuple(item.provenance.frozen_future.calibration_score_set_checksum for item in records)
        ),
        evaluation_score_set_checksum=_aggregate_checksums(
            tuple(item.provenance.frozen_future.evaluation_score_set_checksum for item in records)
        ),
    )
    recalibrated = TemporalDeploymentProvenance(
        state=TemporalState.RECALIBRATED_FUTURE,
        split_protocol=recalibrated_template.split_protocol,
        calibration_role=recalibrated_template.calibration_role,
        evaluation_role=recalibrated_template.evaluation_role,
        coordinate_checksum=recalibrated_template.coordinate_checksum,
        checkpoint_checksum=recalibrated_template.checkpoint_checksum,
        preprocessing_state_set_checksum=recalibrated_template.preprocessing_state_set_checksum,
        split_manifest_checksum=frozen.split_manifest_checksum,
        calibration_score_set_checksum=_aggregate_checksums(
            tuple(item.provenance.recalibrated_future.calibration_score_set_checksum for item in records)
        ),
        evaluation_score_set_checksum=frozen.evaluation_score_set_checksum,
    )
    validate_frozen_recalibrated_pair(frozen, recalibrated)
    _validate_shared_temporal_detector(static, frozen)
    return static, frozen, recalibrated


def _aggregate_checksums(checksums: tuple[Checksum, ...]) -> Checksum:
    return canonical_checksum(checksums)


def _build_client_trajectories(
    *,
    seed: Seed,
    method: FederatedThresholdMethod,
    static_outcome: TemporalMethodOutcome,
    frozen_outcome: TemporalMethodOutcome,
    recalibrated_outcome: TemporalMethodOutcome,
) -> tuple[TemporalClientTrajectory, ...]:
    static_by_id = {client.client.client_id: client for client in static_outcome.clients}
    frozen_by_id = {client.client.client_id: client for client in frozen_outcome.clients}
    recalibrated_by_id = {client.client.client_id: client for client in recalibrated_outcome.clients}
    client_ids = tuple(sorted(frozenset(static_by_id) | frozenset(frozen_by_id) | frozenset(recalibrated_by_id)))
    if not client_ids:
        return ()
    exclusion_reasons = _client_exclusion_reason_map(
        (
            static_outcome.excluded_clients,
            frozen_outcome.excluded_clients,
            recalibrated_outcome.excluded_clients,
        ),
    )
    trajectories: list[TemporalClientTrajectory] = []
    for client_id in client_ids:
        static_client = static_by_id.get(client_id)
        frozen_client = frozen_by_id.get(client_id)
        recalibrated_client = recalibrated_by_id.get(client_id)
        eligible = _client_is_eligible(static_client, frozen_client, recalibrated_client)
        trajectories.append(
            TemporalClientTrajectory(
                seed=seed,
                client_id=client_id,
                threshold_method=method,
                eligible=eligible,
                exclusion_reason=None if eligible else exclusion_reasons.get(client_id, "client_not_evaluable"),
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
            )
        )
    return tuple(trajectories)


def _client_is_eligible(
    static_client: ClientMetricResult | None,
    frozen_client: ClientMetricResult | None,
    recalibrated_client: ClientMetricResult | None,
) -> bool:
    if static_client is None or frozen_client is None or recalibrated_client is None:
        return False
    return (
        static_client.cohort is EvaluationCohort.FPR_EVALUABLE
        and frozen_client.cohort is EvaluationCohort.FPR_EVALUABLE
        and recalibrated_client.cohort is EvaluationCohort.FPR_EVALUABLE
    )


def _client_threshold(client: ClientMetricResult | None) -> MetricValue | None:
    if client is None:
        return None
    return MetricValue(client.threshold.value)


def _client_metric(client: ClientMetricResult | None, metric: MetricId) -> MetricValue | None:
    if client is None:
        return None
    result = metric_by_id(client.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        return None
    return result.value


def _client_exclusion_reason_map(
    excluded_groups: tuple[tuple[ClientIdentity, ...], ...],
) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for group in excluded_groups:
        for item in group:
            reasons.setdefault(item.client_id, "excluded_from_fpr_evaluable_cohort")
    return reasons


def _cohort_exclusion_records(
    cohort: EvaluationCohortManifest,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    exclusions: list[str] = []
    unavailable_reasons: list[str] = []
    for record in sorted(cohort.records, key=lambda item: item.client.client_id):
        if record.fpr_evaluable:
            continue
        client_id = record.client.client_id
        exclusions.append(client_id)
        if record.exclusion_reasons:
            for reason in record.exclusion_reasons:
                unavailable_reasons.append(f"{client_id}:{reason.value}")
        else:
            unavailable_reasons.append(f"{client_id}:not_fpr_evaluable")
    return tuple(exclusions), tuple(unavailable_reasons)


def _union_text(*groups: tuple[str, ...]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item in seen:
                continue
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


def _declaration_identity(
    declaration: ExperimentDeclaration,
    state: TemporalState,
) -> ExternalTemporalExecutionIdentity:
    return ExternalTemporalExecutionIdentity(
        experiment=declaration.id,
        population=declaration.population,
        evidence_role=declaration.role,
        temporal_state=state,
    )


def _temporal_coordinates(partition_seed: Seed, declaration: ExperimentDeclaration) -> TemporalCoordinateSet:
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(partition_seed,)),
    )
    return TemporalCoordinateSet(
        static_reference=_coordinate_for_state(plan, TemporalState.STATIC_REFERENCE),
        frozen_future=_coordinate_for_state(plan, TemporalState.FROZEN_FUTURE),
        recalibrated_future=_coordinate_for_state(plan, TemporalState.RECALIBRATED_FUTURE),
    )


def _coordinate_for_state(plan: ExperimentPlan, state: TemporalState) -> ExperimentCoordinate:
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


def _temporal_campaign_analysis_directory(method: FederatedThresholdMethod) -> Path:
    declaration = _temporal_declaration()
    return (
        OUTPUTS_ROOT
        / ExecutionRootDirectory.BOUNDED_EVIDENCE
        / declaration.id.value
        / declaration.population.value
        / declaration.role.value
        / TemporalArtifactDirectory.ANALYSIS
        / method.value
    )


def _temporal_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    if len(matches) != 1:
        raise ScientificContractError("the temporal experiment must be declared exactly once")
    return matches[0]
