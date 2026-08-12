from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import polars as pl

from datp_core.analysis.metrics.client import (
    calculate_auroc,
    calculate_average_precision,
    calculate_metrics_for_evaluation_score_arrays,
)
from datp_core.analysis.metrics.cohort_construction import cohort_record_for_client
from datp_core.analysis.metrics.cohorts import ClientEligibilityRecord
from datp_core.analysis.metrics.conformal import evaluate_held_out_conformal_coverage
from datp_core.analysis.metrics.confusion import calculate_confusion_counts_for_evaluation_arrays
from datp_core.analysis.metrics.federated import (
    EvaluationDiagnostics,
    FederatedEvaluationArtifacts,
    FederatedEvaluationDocument,
    FederatedEvaluationPublication,
    FederatedEvaluationRequest,
    ShrinkageLambdaEvaluation,
    ThresholdEstimationStageInput,
)
from datp_core.analysis.metrics.fixed_score import FederatedEvaluationScoreArrays
from datp_core.analysis.metrics.fixed_score_validation import validate_evaluation_evidence
from datp_core.analysis.metrics.models import (
    ClientMetricResult,
    FederatedScoreRecord,
    MetricAvailability,
    PopulationMetricResult,
    metric_by_id,
)
from datp_core.analysis.metrics.operating_point import evaluate_held_out_operating_points
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.analysis.metrics.threshold_estimation import (
    ThresholdEstimationDiagnostic,
    evaluate_threshold_estimate,
    sample_efficiency_curve,
)
from datp_core.analysis.operational.alert_burden import AlertBurdenDiagnostic, calculate_alert_burden
from datp_core.analysis.operational.communication import summarize_communication
from datp_core.analysis.operational.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ContractSubject,
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    ScoreArtifactPathText,
    ScoreFrameColumn,
    StableRowId,
    StageOperationId,
)
from datp_core.core.numeric import (
    Ratio,
    ScoreValue,
    ShrinkageWeight,
    ThresholdValue,
)
from datp_core.data.populations.contracts import (
    ClientIdentity,
    PopulationOutcomeLabel,
    population_allowed_evidence_roles,
)
from datp_core.data.registry import population_capabilities
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.coordinates import require_execution_identity
from datp_core.thresholds.contracts import ThresholdAssignment, ThresholdUnavailableResult
from datp_core.thresholds.dispatch import ThresholdConstructionResult
from datp_core.thresholds.policies.cluster import GroupedThresholdResult
from datp_core.thresholds.policies.family import FamilyThresholdResult
from datp_core.thresholds.policies.local import LocalThresholdResult
from datp_core.thresholds.policies.shared import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
)
from datp_core.thresholds.quantiles import unweighted_mean
from datp_core.thresholds.variants.conformal import ConformalThresholdResult
from datp_core.thresholds.variants.federated_statistics import FederatedStatisticsThresholdResult
from datp_core.thresholds.variants.kll import FederatedKllSharedThresholdResult
from datp_core.thresholds.variants.moment import MomentLocalThresholdResult, MomentSharedThresholdResult
from datp_core.thresholds.variants.shrinkage import FixedShrinkageCurveResult, SizeAwareShrinkageThresholdResult


@dataclass(frozen=True, slots=True)
class FederatedEvaluationMetrics:
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult


def prepare_federated_evaluation(request: FederatedEvaluationRequest) -> FederatedEvaluationPublication:
    _validate_temporal_provenance(request)
    metrics = _evaluate(request)
    diagnostics = _evaluate_diagnostics(request, metrics.clients)
    validate_evaluation_evidence(
        request.fixed_score_evidence,
        request.score_manifest,
        request.cohort,
        metrics.clients,
    )
    artifacts = FederatedEvaluationArtifacts(
        clients=metrics.clients,
        population=metrics.population,
        diagnostics=diagnostics,
    )
    document = FederatedEvaluationDocument(
        stage=StageOperationId.EVALUATE_FEDERATED,
        execution_key=request.execution_key,
        score_coordinate=request.score_manifest.coordinate,
        threshold_method=_threshold_method(request.threshold_result),
        evidence_role=request.evidence_role,
        fixed_score_evidence=request.fixed_score_evidence,
        cohort=request.cohort,
        clients=metrics.clients,
        population=metrics.population,
        diagnostics=diagnostics,
        temporal_provenance=request.temporal_provenance,
    )
    return FederatedEvaluationPublication(
        artifacts=artifacts,
        document=document,
    )


def _validate_temporal_provenance(request: FederatedEvaluationRequest) -> None:
    provenance = request.temporal_provenance
    temporal = request.evidence_role is EvidenceRole.TEMPORAL_BOUNDARY
    if not temporal and (provenance is not None or request.temporal_threshold_provenance is not None):
        raise ScientificContractError(
            ErrorMessage("temporal provenance is valid only for temporal-boundary evaluation"),
            subject=request.evidence_role,
        )
    if not temporal:
        return
    if provenance is None or request.temporal_threshold_provenance is None:
        raise ScientificContractError(
            ErrorMessage("temporal evaluation requires score and threshold provenance"),
            subject=request.evidence_role,
        )
    if provenance != request.temporal_threshold_provenance:
        raise ScientificContractError(
            ErrorMessage("temporal threshold provenance must bind the evaluated score state"),
            subject=request.evidence_role,
        )
    provenance.validate_score_manifest(request.score_manifest)
    identity = require_execution_identity(request.execution_identity, request.score_manifest.coordinate.population)
    if identity is None or identity.temporal_state is not provenance.state:
        raise ScientificContractError(
            ErrorMessage("temporal evaluation provenance must match the execution identity state"),
            subject=request.score_manifest.coordinate.population,
        )


def _evaluate(
    request: FederatedEvaluationRequest,
) -> FederatedEvaluationMetrics:
    _validate_evaluation_request(request)
    if isinstance(request.threshold_result, FixedShrinkageCurveResult):
        return _evaluate_shrinkage_curve(request)
    assignments = _assignments(request.threshold_result)

    assignment_map: dict[ClientIdentity, ThresholdValue] = {}
    for item in assignments:
        if item.client in assignment_map:
            raise ScientificContractError(ErrorMessage("threshold assignments cannot repeat a client"))
        assignment_map[item.client] = item.threshold

    fallback_threshold = _deployment_fallback_threshold(assignments, request.threshold_result)

    clients = tuple(
        _evaluate_score_record(request, assignment_map, fallback_threshold, record)
        for record in sorted(request.score_manifest.evaluation_records, key=lambda item: item.scored_client)
    )
    return FederatedEvaluationMetrics(
        clients=clients,
        population=calculate_population_metrics(clients, cohort=request.cohort),
    )


def _validate_evaluation_request(request: FederatedEvaluationRequest) -> None:
    if isinstance(request.threshold_result, ThresholdUnavailableResult):
        raise ScientificContractError(ErrorMessage("unavailable threshold cannot be evaluated"))
    if _threshold_coordinate(request.threshold_result) != request.score_manifest.coordinate:
        raise ScientificContractError(ErrorMessage("threshold and score coordinates must match"))
    if request.cohort.population is not request.score_manifest.coordinate.population:
        raise ScientificContractError(ErrorMessage("evaluation cohort must match score population"))
    population = request.score_manifest.coordinate.population
    allowed = population_allowed_evidence_roles(population)
    if request.evidence_role not in allowed:
        raise ScientificContractError(
            ErrorMessage("evaluation evidence role is not authorized for this population"),
            subject=request.evidence_role,
        )
    if request.evidence_role is EvidenceRole.CONFIRMATORY:
        capabilities = population_capabilities(population)
        if not capabilities.confirmatory_eligible:
            raise ScientificContractError(
                ErrorMessage("confirmatory evidence role requires a confirmatory-eligible population"),
                subject=request.evidence_role,
            )
    identity = require_execution_identity(request.execution_identity, population)
    if identity is not None:
        identity.require_evidence_role(request.evidence_role)


def _evaluate_score_record(
    request: FederatedEvaluationRequest,
    assignment_map: dict[ClientIdentity, ThresholdValue],
    fallback_threshold: ThresholdValue | None,
    record: FederatedScoreRecord,
) -> ClientMetricResult:
    eligibility = cohort_record_for_client(request.cohort, record.scored_client)
    threshold = assignment_map.get(record.scored_client)

    if eligibility is None:
        raise ScientificContractError(ErrorMessage("cohort must cover every evaluated client"))
    if threshold is None:
        if eligibility.calibration_eligible:
            raise ScientificContractError(
                ErrorMessage("calibration-eligible clients require a threshold assignment"),
                subject=ContractSubject.THRESHOLD,
            )
        threshold = fallback_threshold
        if threshold is None:
            raise ScientificContractError(
                ErrorMessage("threshold assignment missing for evaluation client without a deployment fallback"),
                subject=ContractSubject.THRESHOLD,
            )
    if not record.path.is_file():
        raise ArtifactIntegrityError(ErrorMessage("evaluation score artifact is incomplete or changed"))

    score_arrays = _score_arrays(ScoreArtifactPathText(str(record.path)))
    confusion = calculate_confusion_counts_for_evaluation_arrays(
        score_values=score_arrays.score_values,
        attack_mask=score_arrays.attack_mask,
        threshold=threshold,
        attack_assignment_valid=eligibility.attack_evaluable,
    )
    return ClientMetricResult(
        coordinate=request.score_manifest.coordinate,
        threshold_method=_threshold_method(request.threshold_result),
        client=record.scored_client,
        cohort=_evaluation_cohort(eligibility),
        threshold=threshold,
        confusion=confusion,
        metrics=calculate_metrics_for_evaluation_score_arrays(
            confusion=confusion,
            score_arrays=score_arrays,
            fixed_auroc=_score_auroc(ScoreArtifactPathText(str(record.path)), eligibility.attack_evaluable),
            fixed_average_precision=_score_average_precision(
                ScoreArtifactPathText(str(record.path)), eligibility.attack_evaluable
            ),
        ),
        warnings=(),
        evidence_role=request.evidence_role,
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
    shrinkage_curve = (
        _shrinkage_curve_evaluations(request) if isinstance(request.threshold_result, FixedShrinkageCurveResult) else ()
    )
    held_out_operating_points, held_out_operating_point_summary = evaluate_held_out_operating_points(
        clients,
        request.calibration_scores,
        request.target_quantile,
    )
    return EvaluationDiagnostics(
        conformal_coverage=conformal_coverage,
        threshold_estimation=threshold_estimation,
        communication=communication,
        alert_burden=_evaluate_alert_burden(request.traffic_rate_evidence, clients, coordinate),
        held_out_operating_points=held_out_operating_points,
        held_out_operating_point_summary=held_out_operating_point_summary,
        shrinkage_curve=shrinkage_curve,
        calibration_size_ablation=request.calibration_size_ablation,
        sample_efficiency=sample_efficiency_curve(threshold_estimation) if threshold_estimation else (),
    )


def _evaluate_threshold_estimation_input(
    diagnostic: ThresholdEstimationStageInput,
    coordinate: FederatedTrainingCoordinate,
) -> ThresholdEstimationDiagnostic:
    if diagnostic.provenance.coordinate != coordinate:
        raise ScientificContractError(
            ErrorMessage("threshold-estimation diagnostics must use the evaluated score coordinate")
        )
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
                    false_positive_rate=Ratio(false_positive_rate.value),
                    evidence=evidence,
                )
            )
    return tuple(diagnostics)


def _evaluate_shrinkage_curve(
    request: FederatedEvaluationRequest,
) -> FederatedEvaluationMetrics:
    curve = _shrinkage_curve_evaluations(request)
    local_endpoint = ShrinkageWeight(1.0)
    matches = tuple(item for item in curve if item.lambda_weight == local_endpoint)
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage("fixed shrinkage evaluation requires the predeclared local endpoint lambda=1"),
            subject=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        )
    return FederatedEvaluationMetrics(
        clients=matches[0].clients,
        population=matches[0].population,
    )


def _shrinkage_curve_evaluations(request: FederatedEvaluationRequest) -> tuple[ShrinkageLambdaEvaluation, ...]:
    curve_result = request.threshold_result
    if not isinstance(curve_result, FixedShrinkageCurveResult):
        raise ScientificContractError(ErrorMessage("shrinkage curve evaluation requires a shrinkage result"))

    evaluations: list[ShrinkageLambdaEvaluation] = []
    for result in curve_result.points:
        assignments = tuple(ThresholdAssignment(item.client, item.threshold) for item in result.assignments)

        assignment_map: dict[ClientIdentity, ThresholdValue] = {}
        for item in assignments:
            if item.client in assignment_map:
                raise ScientificContractError(ErrorMessage("threshold assignments cannot repeat a client"))
            assignment_map[item.client] = item.threshold

        fallback_threshold = unweighted_mean(tuple(item.threshold for item in assignments))

        clients = tuple(
            _evaluate_score_record(request, assignment_map, fallback_threshold, record)
            for record in sorted(request.score_manifest.evaluation_records, key=lambda item: item.scored_client)
        )
        evaluations.append(
            ShrinkageLambdaEvaluation(
                lambda_weight=result.weight,
                clients=clients,
                population=calculate_population_metrics(clients, cohort=request.cohort),
            )
        )
    return tuple(evaluations)


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
            | FederatedKllSharedThresholdResult()
            | MomentSharedThresholdResult()
            | MomentLocalThresholdResult()
        ):
            return result.assignments
        case SizeAwareShrinkageThresholdResult():
            return tuple(ThresholdAssignment(item.client, item.threshold) for item in result.assignments)
        case FixedShrinkageCurveResult():
            raise ScientificContractError(
                ErrorMessage("multi-lambda shrinkage cannot flatten to one assignment set; use curve evaluation")
            )
        case ConformalThresholdResult():
            return tuple(ThresholdAssignment(item.client, item.threshold) for item in result.assignments)


def _deployment_fallback_threshold(
    assignments: tuple[ThresholdAssignment, ...],
    result: ThresholdConstructionResult,
) -> ThresholdValue | None:
    match result:
        case (
            SharedThresholdResult()
            | PooledSharedQuantileResult()
            | SampleWeightedSharedThresholdResult()
            | MomentSharedThresholdResult()
        ):
            return result.shared_threshold
        case FederatedStatisticsThresholdResult():
            return result.matched_threshold
        case FederatedKllSharedThresholdResult():
            return result.threshold
        case (
            LocalThresholdResult()
            | MomentLocalThresholdResult()
            | FamilyThresholdResult()
            | GroupedThresholdResult()
            | ConformalThresholdResult()
            | SizeAwareShrinkageThresholdResult()
        ):
            if not assignments:
                return None
            return unweighted_mean(tuple(item.threshold for item in assignments))
        case ThresholdUnavailableResult():
            return None
        case FixedShrinkageCurveResult():
            raise ScientificContractError(ErrorMessage("multi-lambda shrinkage requires per-weight evaluation"))


def _threshold_method(result: ThresholdConstructionResult) -> FederatedThresholdMethod:
    return result.method


def _threshold_coordinate(result: ThresholdConstructionResult) -> FederatedTrainingCoordinate:
    return result.coordinate


@lru_cache(maxsize=9)
def _score_arrays(
    path: ScoreArtifactPathText,
) -> FederatedEvaluationScoreArrays:
    required = [
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    ]
    try:
        frame = pl.read_parquet(path, columns=required)
    except pl.exceptions.ColumnNotFoundError as err:
        raise ArtifactIntegrityError(ErrorMessage("evaluation score artifact has an invalid schema")) from err

    data = frame.to_dict(as_series=False)
    scores = tuple(ScoreValue(float(value)) for value in data[required[2]])
    labels = tuple(PopulationOutcomeLabel(str(value)) for value in data[required[1]])
    row_ids = tuple(StableRowId(str(value)) for value in data[required[0]])
    if len(frozenset(row_ids)) != len(row_ids):
        raise ScientificContractError(
            ErrorMessage("evaluation source rows must be unique and stable"), subject=ContractSubject.ROWS
        )
    score_values = np.fromiter((score.value for score in scores), dtype=np.float64, count=len(scores))
    if not np.isfinite(score_values).all():
        raise ScientificContractError(
            ErrorMessage("scores and thresholds must be finite"), subject=ContractSubject.SCORES
        )
    score_values.setflags(write=False)
    attack_mask = np.fromiter(
        (label is PopulationOutcomeLabel.ATTACK for label in labels), dtype=np.bool_, count=len(labels)
    )
    attack_mask.setflags(write=False)
    return FederatedEvaluationScoreArrays(
        scores=scores,
        labels=labels,
        row_ids=row_ids,
        score_values=score_values,
        attack_mask=attack_mask,
    )


@lru_cache(maxsize=9)
def _score_auroc(path: ScoreArtifactPathText, attack_assignment_valid: bool) -> MetricAvailability:
    score_arrays = _score_arrays(path)
    return calculate_auroc(score_arrays.score_values, score_arrays.labels, attack_assignment_valid)


@lru_cache(maxsize=9)
def _score_average_precision(path: ScoreArtifactPathText, attack_assignment_valid: bool) -> MetricAvailability:
    score_arrays = _score_arrays(path)
    return calculate_average_precision(score_arrays.score_values, score_arrays.labels, attack_assignment_valid)
