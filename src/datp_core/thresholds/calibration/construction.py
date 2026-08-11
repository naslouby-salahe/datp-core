from dataclasses import dataclass

from datp_core.analysis.metrics.cohorts import (
    ClientExclusionReason,
    EvaluationCohortManifest,
    EvaluationCohortMembership,
)
from datp_core.analysis.metrics.federated import CalibrationSizeAblationCell, FederatedEvaluationRequest
from datp_core.analysis.metrics.federated_execution import prepare_federated_evaluation
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import EvaluationCohort, EvidenceRole, FederatedThresholdMethod
from datp_core.core.numeric import CalibrationSize, Quantile, ReplicateIndex, SubsampleReplicateCount
from datp_core.data.populations.contracts import ClientIdentity, EligibleCohort, FamilyAssignment
from datp_core.data.registry import population_capabilities
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.thresholds.calibration.eligibility import EligibilityDecision
from datp_core.thresholds.calibration.sampling import CalibrationReplicateManifest
from datp_core.thresholds.calibration.service import CalibrationRequest, calibrate
from datp_core.thresholds.contracts import ThresholdUnavailableResult
from datp_core.thresholds.dispatch import ThresholdConstructionRequest, dispatch_federated_threshold
from datp_core.thresholds.protocols import (
    CALIBRATION_ELIGIBILITY_PROTOCOL,
    CALIBRATION_SIZE_PROTOCOL,
    CalibrationEligibilityProtocol,
    CalibrationSupportRule,
    ClusterThresholdAggregation,
    require_calibration_subsample_replicate_count,
)
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, calibration_scores_from_references


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
    score_manifest: FederatedScoreArtifactManifest
    method: FederatedThresholdMethod
    quantile: Quantile
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    evidence_role: EvidenceRole
    family_by_client: tuple[FamilyAssignment, ...]
    calibration: BuildCalibrationResult
    execution_identity: ExternalTemporalExecutionIdentity | None


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
                    score_manifest=request.score_manifest,
                    threshold_result=threshold,
                    cohort=_cell_cohort(request.cohort, tuple(item.client for item in eligible)),
                    fixed_score_evidence=request.fixed_score_evidence,
                    evidence_role=request.evidence_role,
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
