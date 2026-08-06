"""Held-out federated evaluation over immutable scores and thresholds."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.datasets.registry import population_capabilities
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    ScoreFrameColumn,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum, canonical_json_text
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    Checksum,
    CoverageTarget,
    ScoreValue,
    ThresholdValue,
    checksum_file,
)
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.cohorts import (
    ClientEligibilityRecord,
    EvaluationCohortManifest,
    cohort_record_for_client,
)
from datp_core.evaluation.communication import (
    CommunicationDiagnostic,
    CommunicationMessageDiagnostic,
    summarize_communication,
)
from datp_core.evaluation.conformal_coverage import (
    ConformalCoverageDiagnostic,
    evaluate_held_out_conformal_coverage,
)
from datp_core.evaluation.confusion import calculate_confusion_counts
from datp_core.evaluation.fixed_score.checksums import evaluation_label_checksum, source_row_checksum
from datp_core.evaluation.fixed_score.contracts import FixedScoreEvidence
from datp_core.evaluation.fixed_score.validation import validate_evaluation_evidence, validate_fixed_score_controls
from datp_core.evaluation.models import (
    ClientMetricResult,
    HeldOutBenignScore,
    PopulationMetricResult,
    metric_by_id,
)
from datp_core.evaluation.operational import AlertBurdenDiagnostic, calculate_alert_burden
from datp_core.evaluation.population_metrics import calculate_population_metrics
from datp_core.evaluation.threshold_estimation import (
    ThresholdEstimationDiagnostic,
    ThresholdEstimationProvenance,
    evaluate_threshold_estimate,
)
from datp_core.evaluation.threshold_evidence import VerifiedHeldOutBenignScores
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.protocols.inference import ScoreArtifactManifest, ScoreRecord
from datp_core.protocols.temporal import TemporalDeploymentProvenance
from datp_core.thresholding.assignments import ThresholdAssignment
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.methods.cluster import GroupedThresholdResult
from datp_core.thresholding.methods.conformal import ConformalAssignment, ConformalThresholdResult
from datp_core.thresholding.methods.family import FamilyThresholdResult
from datp_core.thresholding.methods.federated_statistics import FederatedStatisticsThresholdResult
from datp_core.thresholding.methods.local import LocalThresholdResult
from datp_core.thresholding.methods.shared import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
)
from datp_core.thresholding.methods.shrinkage import ShrinkageThresholdResult
from datp_core.thresholding.models import ThresholdConstructionResult


class FederatedEvaluationAssetName(StrEnum):
    DOCUMENT = "federated_evaluation.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class ConformalCoverageStageInput:
    assignment: ConformalAssignment
    target_coverage: CoverageTarget
    held_out_benign_scores: tuple[HeldOutBenignScore, ...]


@dataclass(frozen=True, slots=True)
class ThresholdEstimationStageInput:
    provenance: ThresholdEstimationProvenance
    estimated_threshold: ThresholdValue
    exact_pooled_benign_quantile_reference: ThresholdValue
    verified_benign_scores: VerifiedHeldOutBenignScores

    def __post_init__(self) -> None:
        if self.verified_benign_scores.client != self.provenance.client:
            raise ScientificContractError("threshold-estimation evidence must match the evaluated client")
        if self.verified_benign_scores.coordinate != self.provenance.coordinate:
            raise ScientificContractError("threshold-estimation evidence must match the evaluated coordinate")


@dataclass(frozen=True, slots=True)
class EvaluationDiagnostics:
    conformal_coverage: tuple[ConformalCoverageDiagnostic, ...]
    threshold_estimation: tuple[ThresholdEstimationDiagnostic, ...]
    communication: CommunicationDiagnostic | None
    alert_burden: tuple[AlertBurdenDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class FederatedEvaluationRequest:
    score_manifest: ScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    comparison_fixed_score_evidence: FixedScoreEvidence | None
    evidence_role: EvidenceRole
    conformal_coverage_inputs: tuple[ConformalCoverageStageInput, ...]
    threshold_estimation_inputs: tuple[ThresholdEstimationStageInput, ...]
    communication_messages: tuple[CommunicationMessageDiagnostic, ...]
    traffic_rate_evidence: ValidatedTrafficRateEvidence | None
    temporal_provenance: TemporalDeploymentProvenance | None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None
    execution_identity: ExternalTemporalExecutionIdentity | None


class FederatedEvaluationDocument(StrictModel):
    stage: StageOperationId
    score_coordinate: FederatedTrainingCoordinate
    score_checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    threshold_method: FederatedThresholdMethod
    evidence_role: EvidenceRole
    fixed_score_evidence: FixedScoreEvidence
    cohort: EvaluationCohortManifest
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    temporal_provenance: TemporalDeploymentProvenance | None


@dataclass(frozen=True, slots=True)
class FederatedEvaluationArtifacts:
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics


@dataclass(frozen=True, slots=True)
class FederatedEvaluationPublication:
    artifacts: FederatedEvaluationArtifacts
    document: FederatedEvaluationDocument
    digest: Checksum


def prepare_federated_evaluation(request: FederatedEvaluationRequest) -> FederatedEvaluationPublication:
    _validate_temporal_provenance(request)
    clients, population = _evaluate(request)
    diagnostics = _evaluate_diagnostics(request, clients)
    validate_evaluation_evidence(
        request.fixed_score_evidence,
        request.score_manifest,
        request.cohort,
        clients,
    )
    if request.comparison_fixed_score_evidence is not None:
        validate_fixed_score_controls(
            request.fixed_score_evidence,
            request.comparison_fixed_score_evidence,
            auroc_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
        )
    artifacts = FederatedEvaluationArtifacts(clients=clients, population=population, diagnostics=diagnostics)
    document = FederatedEvaluationDocument(
        stage=StageOperationId.EVALUATE_FEDERATED,
        score_coordinate=request.score_manifest.coordinate,
        score_checkpoint_checksum=request.score_manifest.checkpoint_checksum,
        preprocessing_state_set_checksum=request.score_manifest.preprocessing_state_set_checksum,
        split_manifest_checksum=request.score_manifest.split_manifest_checksum,
        threshold_method=request.threshold_result.method,
        evidence_role=request.evidence_role,
        fixed_score_evidence=request.fixed_score_evidence,
        cohort=request.cohort,
        clients=clients,
        population=population,
        diagnostics=diagnostics,
        temporal_provenance=request.temporal_provenance,
    )
    return FederatedEvaluationPublication(
        artifacts=artifacts,
        document=document,
        digest=canonical_checksum(document),
    )


def write_federated_evaluation(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    (directory / FederatedEvaluationAssetName.DOCUMENT).write_text(
        canonical_json_text(publication.document),
        encoding="utf-8",
    )
    (directory / FederatedEvaluationAssetName.COMPLETE).write_text(publication.digest.value, encoding="utf-8")
    return publication.artifacts


def federated_evaluation_is_reusable(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> bool:
    complete = directory / FederatedEvaluationAssetName.COMPLETE
    document = directory / FederatedEvaluationAssetName.DOCUMENT
    try:
        return (
            complete.is_file()
            and document.is_file()
            and complete.read_text(encoding="utf-8").strip() == publication.digest.value
        )
    except OSError:
        return False


def load_reused_federated_evaluation(
    publication: FederatedEvaluationPublication,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    del directory
    return publication.artifacts


def rebase_federated_evaluation(
    result: FederatedEvaluationArtifacts,
    directory: Path,
) -> FederatedEvaluationArtifacts:
    del directory
    return result


def _validate_temporal_provenance(request: FederatedEvaluationRequest) -> None:
    provenance = request.temporal_provenance
    temporal = request.evidence_role is EvidenceRole.TEMPORAL_BOUNDARY
    if not temporal and (provenance is not None or request.temporal_threshold_provenance is not None):
        raise ScientificContractError(
            "temporal provenance is valid only for temporal-boundary evaluation",
            subject=request.evidence_role,
        )
    if not temporal:
        return
    if provenance is None or request.temporal_threshold_provenance is None:
        raise ScientificContractError(
            "temporal evaluation requires score and threshold provenance",
            subject=request.evidence_role,
        )
    if provenance != request.temporal_threshold_provenance:
        raise ScientificContractError(
            "temporal threshold provenance must bind the evaluated score state",
            subject=request.evidence_role,
        )
    provenance.validate_score_manifest(request.score_manifest)
    identity = require_execution_identity(request.execution_identity, request.score_manifest.coordinate.population)
    if identity is None or identity.temporal_state is not provenance.state:
        raise ScientificContractError(
            "temporal evaluation provenance must match the execution identity state",
            subject=request.score_manifest.coordinate.population,
        )


def _evaluate(
    request: FederatedEvaluationRequest,
) -> tuple[tuple[ClientMetricResult, ...], PopulationMetricResult]:
    _validate_evaluation_request(request)
    assignments = _assignments(request.threshold_result)
    clients = tuple(
        _evaluate_score_record(request, assignments, record)
        for record in sorted(request.score_manifest.evaluation_records, key=lambda item: item.scored_client)
    )
    return clients, calculate_population_metrics(clients)


def _validate_evaluation_request(request: FederatedEvaluationRequest) -> None:
    if isinstance(request.threshold_result, ThresholdUnavailableResult):
        raise ScientificContractError("unavailable threshold cannot be evaluated")
    if request.threshold_result.coordinate != request.score_manifest.coordinate:
        raise ScientificContractError("threshold and score coordinates must match")
    if request.cohort.population is not request.score_manifest.coordinate.population:
        raise ScientificContractError("evaluation cohort must match score population")
    capabilities = population_capabilities(request.score_manifest.coordinate.population)
    if request.evidence_role is not capabilities.evidentiary_role:
        raise ScientificContractError(
            "evaluation evidence role must match the population capability contract",
            subject=request.evidence_role,
        )
    identity = require_execution_identity(request.execution_identity, request.score_manifest.coordinate.population)
    if identity is not None:
        identity.require_evidence_role(request.evidence_role)


def _evaluate_score_record(
    request: FederatedEvaluationRequest,
    assignments: tuple[ThresholdAssignment, ...],
    record: ScoreRecord,
) -> ClientMetricResult:
    threshold = _threshold_for_client(assignments, record.scored_client)
    eligibility = cohort_record_for_client(request.cohort, record.scored_client)
    if threshold is None or eligibility is None:
        raise ScientificContractError("threshold and cohort must cover every evaluated client")
    if not record.path.is_file() or checksum_file(record.path) != record.checksum:
        raise ArtifactIntegrityError("evaluation score artifact is incomplete or changed")
    scores, labels, rows = _score_arrays(pl.read_parquet(record.path))
    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=rows,
        threshold=threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=eligibility.attack_evaluable,
    )
    return ClientMetricResult(
        coordinate=request.score_manifest.coordinate,
        threshold_method=request.threshold_result.method,
        client=record.scored_client,
        cohort=_evaluation_cohort(eligibility),
        threshold=threshold,
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=request.evidence_role,
        evaluation_score_checksum=record.checksum,
        evaluation_label_checksum=evaluation_label_checksum(labels),
        source_row_checksum=source_row_checksum(rows),
    )


def _evaluation_cohort(record: ClientEligibilityRecord) -> EvaluationCohort:
    if record.fpr_evaluable:
        return EvaluationCohort.FPR_EVALUABLE
    if record.deployment_fallback:
        return EvaluationCohort.DEPLOYMENT_FALLBACK
    return EvaluationCohort.UNAVAILABLE


def _evaluate_diagnostics(
    request: FederatedEvaluationRequest,
    clients: tuple[ClientMetricResult, ...],
) -> EvaluationDiagnostics:
    coordinate = request.score_manifest.coordinate
    conformal_coverage = tuple(
        evaluate_held_out_conformal_coverage(
            diagnostic.assignment,
            coordinate,
            coordinate.training_seed,
            diagnostic.target_coverage,
            diagnostic.held_out_benign_scores,
        )
        for diagnostic in request.conformal_coverage_inputs
    )
    threshold_estimation = tuple(
        _evaluate_threshold_estimation_input(diagnostic, coordinate)
        for diagnostic in request.threshold_estimation_inputs
    )
    communication = (
        None
        if not request.communication_messages
        else summarize_communication(coordinate.training_seed, coordinate, request.communication_messages)
    )
    return EvaluationDiagnostics(
        conformal_coverage=conformal_coverage,
        threshold_estimation=threshold_estimation,
        communication=communication,
        alert_burden=_evaluate_alert_burden(request.traffic_rate_evidence, clients, coordinate),
    )


def _evaluate_threshold_estimation_input(
    diagnostic: ThresholdEstimationStageInput,
    coordinate: FederatedTrainingCoordinate,
) -> ThresholdEstimationDiagnostic:
    if diagnostic.provenance.coordinate != coordinate:
        raise ScientificContractError("threshold-estimation diagnostics must use the evaluated score coordinate")
    return evaluate_threshold_estimate(
        provenance=diagnostic.provenance,
        estimated_threshold=diagnostic.estimated_threshold,
        exact_pooled_benign_quantile_reference=diagnostic.exact_pooled_benign_quantile_reference,
        verified_benign_scores=diagnostic.verified_benign_scores,
    )


def _evaluate_alert_burden(
    evidence: ValidatedTrafficRateEvidence | None,
    clients: tuple[ClientMetricResult, ...],
    coordinate: FederatedTrainingCoordinate,
) -> tuple[AlertBurdenDiagnostic, ...]:
    if evidence is None:
        return ()
    diagnostics: list[AlertBurdenDiagnostic] = []
    for client in clients:
        false_positive_rate = metric_by_id(client.metrics, MetricId.FALSE_POSITIVE_RATE).value
        if false_positive_rate is not None:
            diagnostics.append(
                calculate_alert_burden(
                    client=client.client,
                    coordinate=coordinate,
                    training_seed=coordinate.training_seed,
                    false_positive_rate=false_positive_rate.value,
                    evidence=evidence,
                )
            )
    return tuple(diagnostics)


def _assignments(result: ThresholdConstructionResult) -> tuple[ThresholdAssignment, ...]:
    match result:
        case ThresholdUnavailableResult():
            return ()
        case (
            SharedThresholdResult()
            | PooledSharedQuantileResult()
            | SampleWeightedSharedThresholdResult()
            | LocalThresholdResult()
            | FamilyThresholdResult()
            | GroupedThresholdResult()
            | FederatedStatisticsThresholdResult()
        ):
            return result.assignments
        case ShrinkageThresholdResult():
            return tuple(ThresholdAssignment(item.client, item.blended_threshold) for item in result.assignments)
        case ConformalThresholdResult():
            return tuple(ThresholdAssignment(item.client, item.threshold) for item in result.assignments)


def _threshold_for_client(
    assignments: tuple[ThresholdAssignment, ...],
    client: ClientIdentity,
) -> ThresholdValue | None:
    matches = tuple(item.threshold for item in assignments if item.client == client)
    if len(matches) > 1:
        raise ScientificContractError("threshold assignments cannot repeat a client")
    return matches[0] if matches else None


def _score_arrays(
    frame: pl.DataFrame,
) -> tuple[tuple[ScoreValue, ...], tuple[PopulationOutcomeLabel, ...], tuple[str, ...]]:
    required = (
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    )
    if any(column not in frame.columns for column in required):
        raise ArtifactIntegrityError("evaluation score artifact has an invalid schema")
    return (
        tuple(ScoreValue(float(value)) for value in frame[required[2]].to_list()),
        tuple(PopulationOutcomeLabel(str(value)) for value in frame[required[1]].to_list()),
        tuple(str(value) for value in frame[required[0]].to_list()),
    )
