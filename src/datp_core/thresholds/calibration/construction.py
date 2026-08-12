from dataclasses import dataclass
from itertools import combinations
from typing import cast

from datp_core.analysis.metrics.cohorts import (
    ClientExclusionReason,
    EvaluationCohortManifest,
    EvaluationCohortMembership,
)
from datp_core.analysis.metrics.federated import (
    CalibrationSizeAblationCell,
    FederatedEvaluationRequest,
    OnboardingCalibrationCell,
    SharedContributorOmissionCell,
)
from datp_core.analysis.metrics.federated_execution import prepare_federated_evaluation
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import CoordinateStableKey, EvaluationCohort, EvidenceRole, FederatedThresholdMethod
from datp_core.core.numeric import (
    CalibrationSize,
    OnboardingCalibrationSize,
    Quantile,
    ReplicateIndex,
    SubsampleReplicateCount,
)
from datp_core.data.populations.contracts import (
    ClientIdentity,
    EligibleCohort,
    FamilyAssignment,
    PopulationCapabilities,
)
from datp_core.data.registry import population_capabilities
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.thresholds.calibration.eligibility import EligibilityDecision, load_benign_calibration_references
from datp_core.thresholds.calibration.sampling import CalibrationReplicateManifest, build_calibration_replicate
from datp_core.thresholds.calibration.service import CalibrationRequest, calibrate, eligible_calibration_scores
from datp_core.thresholds.contracts import (
    OnboardingThresholdResult,
    ThresholdAssignment,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
)
from datp_core.thresholds.dispatch import (
    ThresholdConstructionRequest,
    ThresholdConstructionResult,
    dispatch_federated_threshold,
)
from datp_core.thresholds.policies.family import FamilyThresholdResult
from datp_core.thresholds.policies.shared import SharedThresholdResult
from datp_core.thresholds.protocols import (
    CALIBRATION_ELIGIBILITY_PROTOCOL,
    CALIBRATION_SIZE_PROTOCOL,
    ONBOARDING_CALIBRATION_PROTOCOL,
    CalibrationEligibilityProtocol,
    CalibrationSupportRule,
    ClusterThresholdAggregation,
    require_calibration_subsample_replicate_count,
)
from datp_core.thresholds.quantiles import (
    ClientBenignCalibrationScores,
    calibration_scores_from_references,
    local_quantile,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationReplicateLookup:
    manifests: tuple[CalibrationReplicateManifest, ...]

    def __post_init__(self) -> None:
        keys = tuple((manifest.client, manifest.replicate_index) for manifest in self.manifests)
        if len(frozenset(keys)) != len(keys):
            raise ScientificContractError(
                ErrorMessage("calibration replicate manifests must have unique (client, replicate_index) keys"),
                subject=None,
            )

    def get(self, client: ClientIdentity, replicate_index: ReplicateIndex) -> CalibrationReplicateManifest | None:
        for manifest in self.manifests:
            if manifest.client == client and manifest.replicate_index == replicate_index:
                return manifest
        return None


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildCalibrationRequest:
    score_manifest: FederatedScoreArtifactManifest
    protocol: CalibrationEligibilityProtocol
    calibration_sizes: tuple[CalibrationSize, ...]
    replicate_count: SubsampleReplicateCount


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildCalibrationResult:
    eligibility: tuple[EligibilityDecision, ...]
    eligible_clients: EligibleCohort
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCalibrationSizeAblationRequest:
    execution_key: CoordinateStableKey
    score_manifest: FederatedScoreArtifactManifest
    method: FederatedThresholdMethod
    quantile: Quantile
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    evidence_role: EvidenceRole
    family_by_client: tuple[FamilyAssignment, ...]
    calibration: BuildCalibrationResult
    execution_identity: ExternalTemporalExecutionIdentity | None


@dataclass(frozen=True, slots=True, kw_only=True)
class OnboardingTargetCalibration:
    target: ClientIdentity
    full_target_scores: ClientBenignCalibrationScores
    other_full_scores: tuple[ClientBenignCalibrationScores, ...]
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]

    def subsample(
        self,
        size: OnboardingCalibrationSize,
        replicate_index: ReplicateIndex,
    ) -> ClientBenignCalibrationScores | None:
        if size.value == 0:
            return None
        matches = tuple(
            manifest for manifest in self.replicate_manifests if manifest.replicate_index == replicate_index
        )
        if len(matches) != 1:
            raise ScientificContractError(ErrorMessage("onboarding target replicate must resolve exactly once"))
        samples = tuple(item for item in matches[0].subsamples if item.size.value == size.value)
        if len(samples) != 1:
            raise ScientificContractError(ErrorMessage("onboarding target subsample must resolve exactly once"))
        return calibration_scores_from_references(
            client=self.target,
            coordinate=matches[0].coordinate,
            references=samples[0].references,
        )

    def scores_for_cell(
        self,
        size: OnboardingCalibrationSize,
        replicate_index: ReplicateIndex,
    ) -> tuple[ClientBenignCalibrationScores, ...]:
        """Return full non-target calibration pools plus the target's sole cell sample."""
        target_scores = self.subsample(size, replicate_index)
        if target_scores is None:
            return self.other_full_scores
        return tuple(sorted((*self.other_full_scores, target_scores), key=lambda item: item.client))


@dataclass(frozen=True, slots=True)
class OnboardingThresholdConstruction:
    result: ThresholdConstructionResult | None
    unavailable_reason: ThresholdInfeasibilityReason | None
    family_fallback: bool


MINIMUM_REMAINING_SHARED_CONTRIBUTORS = 5


def exhaustive_shared_contributor_omissions(
    clients: tuple[ClientIdentity, ...],
) -> tuple[tuple[ClientIdentity, ...], ...]:
    ordered = tuple(sorted(clients))
    if len(frozenset(ordered)) != len(ordered):
        raise ScientificContractError(ErrorMessage("shared contributor candidates must be unique"))
    return tuple(
        omission
        for omitted_count in range(5)
        if len(ordered) - omitted_count >= MINIMUM_REMAINING_SHARED_CONTRIBUTORS
        for omission in combinations(ordered, omitted_count)
    )


def construct_shared_contributor_omission_cells(
    request: ConstructCalibrationSizeAblationRequest,
    calibration_scores: tuple[ClientBenignCalibrationScores, ...],
) -> tuple[SharedContributorOmissionCell, ...]:
    if request.method is not FederatedThresholdMethod.SHARED_THRESHOLD:
        return ()
    by_client = {item.client: item for item in calibration_scores}
    cells: list[SharedContributorOmissionCell] = []
    capabilities = population_capabilities(request.score_manifest.coordinate.population)
    for omitted in exhaustive_shared_contributor_omissions(tuple(by_client)):
        contributors = tuple(item for client, item in sorted(by_client.items()) if client not in frozenset(omitted))
        result = dispatch_federated_threshold(
            ThresholdConstructionRequest(
                method=FederatedThresholdMethod.SHARED_THRESHOLD,
                coordinate=request.score_manifest.coordinate,
                quantile=request.quantile,
                capabilities=capabilities,
                eligible=contributors,
                family_by_client=request.family_by_client,
                support_rule=CalibrationSupportRule.DECLARED_SIZE_ABLATION,
                cluster_threshold_aggregation=None,
            )
        )
        if not isinstance(result, SharedThresholdResult):
            raise ScientificContractError(ErrorMessage("contributor omission must construct a shared threshold"))
        all_assignments = tuple(ThresholdAssignment(client, result.shared_threshold) for client in sorted(by_client))
        evaluation_result = OnboardingThresholdResult(
            coordinate=request.score_manifest.coordinate,
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            assignments=all_assignments,
        )
        publication = prepare_federated_evaluation(
            FederatedEvaluationRequest(
                execution_key=request.execution_key,
                score_manifest=request.score_manifest,
                threshold_result=evaluation_result,
                cohort=request.cohort,
                fixed_score_evidence=request.fixed_score_evidence,
                evidence_role=request.evidence_role,
                calibration_scores=calibration_scores,
                target_quantile=request.quantile,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                temporal_provenance=None,
                temporal_threshold_provenance=None,
                execution_identity=request.execution_identity,
            )
        )
        cells.append(
            SharedContributorOmissionCell(
                omitted_clients=omitted,
                shared_threshold=result.shared_threshold,
                clients=publication.artifacts.clients,
                population=publication.artifacts.population,
                held_out_operating_point_summary=publication.artifacts.diagnostics.held_out_operating_point_summary,
            )
        )
    return tuple(cells)


def construct_onboarding_calibration_cell(
    *,
    target_calibration: OnboardingTargetCalibration,
    size: OnboardingCalibrationSize,
    replicate_index: ReplicateIndex,
    method: FederatedThresholdMethod,
    quantile: Quantile,
    capabilities: PopulationCapabilities,
    family_by_client: tuple[FamilyAssignment, ...],
    request: ConstructCalibrationSizeAblationRequest,
) -> OnboardingCalibrationCell:
    construction = construct_onboarding_threshold(
        target_calibration, size, replicate_index, method, quantile, capabilities, family_by_client
    )
    full_local = local_quantile(target_calibration.full_target_scores, quantile).value
    if construction.result is None:
        return OnboardingCalibrationCell(
            target_client=target_calibration.target,
            calibration_size=size,
            replicate_index=replicate_index,
            method=method,
            target_metrics=None,
            target_threshold=None,
            full_calibration_local_threshold=full_local,
            unavailable_reason=construction.unavailable_reason,
            family_fallback=construction.family_fallback,
        )
    calibration_scores = target_calibration.scores_for_cell(size, replicate_index)
    publication = prepare_federated_evaluation(
        FederatedEvaluationRequest(
            execution_key=request.execution_key,
            score_manifest=request.score_manifest,
            threshold_result=construction.result,
            cohort=request.cohort,
            fixed_score_evidence=request.fixed_score_evidence,
            evidence_role=request.evidence_role,
            calibration_scores=calibration_scores,
            target_quantile=quantile,
            conformal_coverage_inputs=(),
            threshold_estimation_inputs=(),
            communication_messages=(),
            traffic_rate_evidence=None,
            temporal_provenance=None,
            temporal_threshold_provenance=None,
            execution_identity=request.execution_identity,
        )
    )
    target_metrics = next(item for item in publication.artifacts.clients if item.client == target_calibration.target)
    return OnboardingCalibrationCell(
        target_client=target_calibration.target,
        calibration_size=size,
        replicate_index=replicate_index,
        method=method,
        target_metrics=target_metrics,
        target_threshold=target_metrics.threshold,
        full_calibration_local_threshold=full_local,
        unavailable_reason=None,
        family_fallback=construction.family_fallback,
    )


def construct_onboarding_threshold(
    target_calibration: OnboardingTargetCalibration,
    size: OnboardingCalibrationSize,
    replicate_index: ReplicateIndex,
    method: FederatedThresholdMethod,
    quantile: Quantile,
    capabilities: PopulationCapabilities,
    family_by_client: tuple[FamilyAssignment, ...],
) -> OnboardingThresholdConstruction:
    eligible = target_calibration.scores_for_cell(size, replicate_index)
    if size.value > 0:
        result = dispatch_federated_threshold(
            ThresholdConstructionRequest(
                method=method,
                coordinate=target_calibration.full_target_scores.coordinate,
                quantile=quantile,
                capabilities=capabilities,
                eligible=eligible,
                family_by_client=family_by_client,
                support_rule=CalibrationSupportRule.DECLARED_SIZE_ABLATION,
                cluster_threshold_aggregation=(
                    ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
                    if method is FederatedThresholdMethod.CLUSTER_THRESHOLD
                    else None
                ),
            )
        )
        return OnboardingThresholdConstruction(
            result=None if isinstance(result, ThresholdUnavailableResult) else result,
            unavailable_reason=None if not isinstance(result, ThresholdUnavailableResult) else result.reason,
            family_fallback=False,
        )
    if method is FederatedThresholdMethod.LOCAL_THRESHOLD:
        return OnboardingThresholdConstruction(
            None,
            ThresholdInfeasibilityReason.UNAVAILABLE_NO_LOCAL_CALIBRATION,
            False,
        )
    if method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
        return OnboardingThresholdConstruction(None, ThresholdInfeasibilityReason.UNAVAILABLE_NO_FINGERPRINT, False)
    result = dispatch_federated_threshold(
        ThresholdConstructionRequest(
            method=method,
            coordinate=target_calibration.full_target_scores.coordinate,
            quantile=quantile,
            capabilities=capabilities,
            eligible=eligible,
            family_by_client=family_by_client,
            support_rule=CalibrationSupportRule.DECLARED_SIZE_ABLATION,
            cluster_threshold_aggregation=None,
        )
    )
    if isinstance(result, ThresholdUnavailableResult):
        return OnboardingThresholdConstruction(None, result.reason, False)
    if method is FederatedThresholdMethod.FAMILY_THRESHOLD:
        if not isinstance(result, FamilyThresholdResult):
            raise ScientificContractError(ErrorMessage("onboarding family construction returned an invalid result"))
        assignments = result.assignments
    elif method is FederatedThresholdMethod.SHARED_THRESHOLD:
        if not isinstance(result, SharedThresholdResult):
            raise ScientificContractError(ErrorMessage("onboarding shared construction returned an invalid result"))
        assignments = result.assignments
    else:
        raise ScientificContractError(ErrorMessage("onboarding m=0 supports only shared and family fallbacks"))
    fallback = False
    if method is FederatedThresholdMethod.FAMILY_THRESHOLD:
        family_result = cast(FamilyThresholdResult, result)
        target_family = next(item.family for item in family_by_client if item.client == target_calibration.target)
        family_threshold = next(
            (
                item.family_threshold
                for item in family_result.families
                if item.family_id == target_family and item.family_threshold is not None
            ),
            None,
        )
        if family_threshold is None:
            shared = dispatch_federated_threshold(
                ThresholdConstructionRequest(
                    method=FederatedThresholdMethod.SHARED_THRESHOLD,
                    coordinate=target_calibration.full_target_scores.coordinate,
                    quantile=quantile,
                    capabilities=capabilities,
                    eligible=eligible,
                    family_by_client=family_by_client,
                    support_rule=CalibrationSupportRule.DECLARED_SIZE_ABLATION,
                    cluster_threshold_aggregation=None,
                )
            )
            if not isinstance(shared, SharedThresholdResult):
                raise ScientificContractError(
                    ErrorMessage("onboarding family fallback must construct a shared threshold")
                )
            family_threshold = shared.shared_threshold
            fallback = True
        target_threshold = family_threshold
    else:
        target_threshold = cast(SharedThresholdResult, result).shared_threshold
    return OnboardingThresholdConstruction(
        OnboardingThresholdResult(
            coordinate=target_calibration.full_target_scores.coordinate,
            threshold_method=method,
            assignments=(*assignments, ThresholdAssignment(target_calibration.target, target_threshold)),
        ),
        None,
        fallback,
    )


def build_calibration(request: BuildCalibrationRequest) -> BuildCalibrationResult:
    result = calibrate(
        CalibrationRequest(
            score_manifest=request.score_manifest,
            protocol=request.protocol,
            calibration_sizes=request.calibration_sizes,
            replicate_count=request.replicate_count,
        )
    )
    return BuildCalibrationResult(
        eligibility=result.eligibility,
        eligible_clients=result.eligible_clients,
        replicate_manifests=result.replicate_manifests,
    )


def build_declared_calibration(score_manifest: FederatedScoreArtifactManifest) -> BuildCalibrationResult:

    return build_calibration(
        BuildCalibrationRequest(
            score_manifest=score_manifest,
            protocol=CALIBRATION_ELIGIBILITY_PROTOCOL,
            calibration_sizes=CALIBRATION_SIZE_PROTOCOL.sizes,
            replicate_count=require_calibration_subsample_replicate_count(),
        )
    )


def build_onboarding_target_calibration(
    score_manifest: FederatedScoreArtifactManifest,
    target: ClientIdentity,
) -> OnboardingTargetCalibration:
    full_scores = eligible_calibration_scores(score_manifest)
    by_client = {item.client: item for item in full_scores}
    target_full = by_client.get(target)
    if target_full is None:
        raise ScientificContractError(ErrorMessage("onboarding target lacks canonical eligible calibration support"))
    record = next((item for item in score_manifest.calibration_records if item.scored_client == target), None)
    if record is None:
        raise ScientificContractError(ErrorMessage("onboarding target lacks a calibration score artifact"))
    references = load_benign_calibration_references(record)
    positive_sizes = tuple(CalibrationSize(size.value) for size in ONBOARDING_CALIBRATION_PROTOCOL.replicated_sizes)
    manifests = tuple(
        build_calibration_replicate(
            client=target,
            coordinate=score_manifest.coordinate,
            training_seed=score_manifest.coordinate.training_seed,
            replicate_index=ReplicateIndex(index),
            references=references,
            sizes=positive_sizes,
        )
        for index in range(ONBOARDING_CALIBRATION_PROTOCOL.replicate_count.value)
    )
    return OnboardingTargetCalibration(
        target=target,
        full_target_scores=target_full,
        other_full_scores=tuple(item for item in full_scores if item.client != target),
        replicate_manifests=manifests,
    )


def construct_calibration_size_ablation(
    request: ConstructCalibrationSizeAblationRequest,
) -> tuple[CalibrationSizeAblationCell, ...]:

    cells: list[CalibrationSizeAblationCell] = []
    capabilities = population_capabilities(request.score_manifest.coordinate.population)
    replicate_count = require_calibration_subsample_replicate_count()
    by_client_replicate = CalibrationReplicateLookup(manifests=request.calibration.replicate_manifests)
    for size in CALIBRATION_SIZE_PROTOCOL.sizes:
        for replicate_value in range(replicate_count.value):
            replicate_index = ReplicateIndex(replicate_value)
            eligible = _eligible_scores_for_size(
                request.calibration.eligible_clients,
                by_client_replicate,
                size,
                replicate_index,
            )
            if not eligible:
                continue
            threshold = dispatch_federated_threshold(
                ThresholdConstructionRequest(
                    method=request.method,
                    coordinate=request.score_manifest.coordinate,
                    quantile=request.quantile,
                    capabilities=capabilities,
                    eligible=eligible,
                    family_by_client=request.family_by_client,
                    support_rule=CalibrationSupportRule.DECLARED_SIZE_ABLATION,
                    cluster_threshold_aggregation=(
                        ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
                        if request.method is FederatedThresholdMethod.CLUSTER_THRESHOLD
                        else None
                    ),
                )
            )
            if isinstance(threshold, ThresholdUnavailableResult):
                continue
            publication = prepare_federated_evaluation(
                FederatedEvaluationRequest(
                    execution_key=request.execution_key,
                    score_manifest=request.score_manifest,
                    threshold_result=threshold,
                    cohort=_cell_cohort(request.cohort, tuple(item.client for item in eligible)),
                    fixed_score_evidence=request.fixed_score_evidence,
                    evidence_role=request.evidence_role,
                    calibration_scores=eligible,
                    target_quantile=request.quantile,
                    conformal_coverage_inputs=(),
                    threshold_estimation_inputs=(),
                    communication_messages=(),
                    traffic_rate_evidence=None,
                    temporal_provenance=None,
                    temporal_threshold_provenance=None,
                    execution_identity=request.execution_identity,
                    calibration_size_ablation=(),
                )
            )
            cells.append(
                CalibrationSizeAblationCell(
                    calibration_size=size,
                    replicate_index=replicate_index,
                    method=request.method,
                    clients=publication.artifacts.clients,
                    population=publication.artifacts.population,
                    held_out_operating_points=publication.artifacts.diagnostics.held_out_operating_points,
                    held_out_operating_point_summary=publication.artifacts.diagnostics.held_out_operating_point_summary,
                )
            )
    if not cells:
        raise ScientificContractError(
            ErrorMessage("calibration-size ablation produced no evaluable size/replicate cells"),
            subject=request.method,
        )
    return tuple(cells)


def _eligible_scores_for_size(
    eligible_clients: EligibleCohort,
    by_client_replicate: CalibrationReplicateLookup,
    size: CalibrationSize,
    replicate_index: ReplicateIndex,
) -> tuple[ClientBenignCalibrationScores, ...]:
    scores: list[ClientBenignCalibrationScores] = []
    for client in eligible_clients:
        manifest = by_client_replicate.get(client, replicate_index)
        if manifest is None:
            continue
        matches = tuple(item for item in manifest.subsamples if item.size == size)
        if len(matches) != 1:
            continue
        subsample = matches[0]
        scores.append(
            calibration_scores_from_references(
                client=client,
                coordinate=manifest.coordinate,
                references=subsample.references,
            )
        )
    return tuple(scores)


def _cell_cohort(
    cohort: EvaluationCohortManifest,
    feasible_clients: tuple[ClientIdentity, ...],
) -> EvaluationCohortManifest:
    feasible = frozenset(feasible_clients)
    records = tuple(
        record
        if record.client in feasible
        else record.model_copy(
            update={
                "calibration_eligible": False,
                "fpr_evaluable": False,
                "deployment_fallback": True,
                "exclusion_reasons": (*record.exclusion_reasons, ClientExclusionReason.INSUFFICIENT_CALIBRATION_SIZE),
            }
        )
        for record in cohort.records
    )
    memberships = tuple(
        membership
        for membership in cohort.memberships
        if membership.client in feasible or membership.cohort is EvaluationCohort.ATTACK_EVALUABLE
    ) + tuple(
        EvaluationCohortMembership(
            client=record.client,
            cohort=EvaluationCohort.DEPLOYMENT_FALLBACK,
            reasons=(ClientExclusionReason.INSUFFICIENT_CALIBRATION_SIZE,),
        )
        for record in records
        if record.client not in feasible
    )
    return cohort.model_copy(update={"records": records, "memberships": memberships})
