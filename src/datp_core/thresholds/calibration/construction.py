"""Benign-only calibration eligibility, subsampling, and size-ablation construction."""

from dataclasses import dataclass

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.federated import CalibrationSizeAblationCell, FederatedEvaluationRequest
from datp_core.analysis.metrics.federated_execution import prepare_federated_evaluation
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import EvidenceRole, FederatedThresholdMethod
from datp_core.core.numeric import CalibrationSize, Quantile, ReplicateIndex, SubsampleReplicateCount
from datp_core.data.populations.contracts import ClientIdentity, EligibleCohort, FamilyAssignment
from datp_core.data.registry import population_capabilities
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.thresholds.calibration.eligibility import EligibilityDecision
from datp_core.thresholds.calibration.sampling import CalibrationReplicateManifest, CalibrationSubsample
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
    """Typed lookup for calibration replicate manifests by (client, replicate_index) coordinate."""

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
    """Construct the declared calibration-size ablation lattice once replication is specified."""
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
    """Evaluate the declared size × replicate grid on the unchanged held-out test set."""
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
                    cohort=request.cohort,
                    fixed_score_evidence=request.fixed_score_evidence,
                    comparison_fixed_score_evidence=None,
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
                score_set_checksum=_subsample_checksum(manifest, subsample),
            )
        )
    return tuple(scores)


def _subsample_checksum(manifest: CalibrationReplicateManifest, subsample: CalibrationSubsample) -> Checksum:
    payload = "|".join(
        (
            manifest.client.client_id.value,
            str(manifest.replicate_index.value),
            str(subsample.size.value),
            *sorted(str(item.stable_row_id) for item in subsample.references),
        )
    )
    return Checksum.from_text(payload)
