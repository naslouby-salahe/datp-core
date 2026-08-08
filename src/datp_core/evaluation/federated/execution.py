import polars as pl

from datp_core.data.registry import population_capabilities
from datp_core.datasets.partitioning.contracts import (
    ClientIdentity,
    PopulationOutcomeLabel,
    population_allowed_evidence_roles,
)
from datp_core.domain.enums import (
    ContractSubject,
    EvaluationCohort,
    EvidenceRole,
    MetricId,
    PartitionRole,
    ScoreFrameColumn,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.checksums import checksum_file
from datp_core.domain.values.identifiers import StableRowId
from datp_core.domain.values.ratios import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    Ratio,
    ScoreValue,
    ShrinkageWeight,
    ThresholdValue,
)
from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.evaluation.cohort.construction import cohort_record_for_client
from datp_core.analysis.metrics.cohorts import ClientEligibilityRecord
from datp_core.evaluation.communication import summarize_communication
from datp_core.analysis.metrics.conformal import evaluate_held_out_conformal_coverage
from datp_core.analysis.metrics.confusion import calculate_confusion_counts
from datp_core.evaluation.federated.contracts import (
    EvaluationDiagnostics,
    FederatedEvaluationArtifacts,
    FederatedEvaluationDocument,
    FederatedEvaluationPublication,
    FederatedEvaluationRequest,
    ShrinkageLambdaEvaluation,
    ThresholdEstimationStageInput,
)
from datp_core.evaluation.fixed_score.checksums import evaluation_label_checksum, source_row_checksum
from datp_core.evaluation.fixed_score.validation import validate_evaluation_evidence, validate_fixed_score_controls
from datp_core.analysis.metrics.models import (
    ClientMetricResult,
    FederatedScoreRecord,
    PopulationMetricResult,
    metric_by_id,
)
from datp_core.evaluation.operational import AlertBurdenDiagnostic, calculate_alert_burden
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.analysis.metrics.threshold_estimation import (
    ThresholdEstimationDiagnostic,
    evaluate_threshold_estimate,
    sample_efficiency_curve,
)
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.protocols.experiments import require_execution_identity
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
from datp_core.thresholds.variants.shrinkage import ShrinkageThresholdResult


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
    if isinstance(request.threshold_result, ShrinkageThresholdResult):
        return _evaluate_shrinkage_curve(request)
    assignments = _assignments(request.threshold_result)

    assignment_map: dict[ClientIdentity, ThresholdValue] = {}
    for item in assignments:
        if item.client in assignment_map:
            raise ScientificContractError("threshold assignments cannot repeat a client")
        assignment_map[item.client] = item.threshold

    fallback_threshold = _deployment_fallback_threshold(assignments, request.threshold_result)

    clients = tuple(
        _evaluate_score_record(request, assignment_map, fallback_threshold, record)
        for record in sorted(request.score_manifest.evaluation_records, key=lambda item: item.scored_client)
    )
    return clients, calculate_population_metrics(clients, cohort=request.cohort)


def _validate_evaluation_request(request: FederatedEvaluationRequest) -> None:
    if isinstance(request.threshold_result, ThresholdUnavailableResult):
        raise ScientificContractError("unavailable threshold cannot be evaluated")
    if request.threshold_result.coordinate != request.score_manifest.coordinate:
        raise ScientificContractError("threshold and score coordinates must match")
    if request.cohort.population is not request.score_manifest.coordinate.population:
        raise ScientificContractError("evaluation cohort must match score population")
    population = request.score_manifest.coordinate.population
    allowed = population_allowed_evidence_roles(population)
    if request.evidence_role not in allowed:
        raise ScientificContractError(
            "evaluation evidence role is not authorized for this population",
            subject=request.evidence_role,
        )
    if request.evidence_role is EvidenceRole.CONFIRMATORY:
        capabilities = population_capabilities(population)
        if not capabilities.confirmatory_eligible:
            raise ScientificContractError(
                "confirmatory evidence role requires a confirmatory-eligible population",
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
        raise ScientificContractError("cohort must cover every evaluated client")
    if threshold is None:
        if eligibility.calibration_eligible:
            raise ScientificContractError(
                "calibration-eligible clients require a threshold assignment",
                subject=ContractSubject.THRESHOLD,
            )
        threshold = fallback_threshold
        if threshold is None:
            raise ScientificContractError(
                "threshold assignment missing for evaluation client without a deployment fallback",
                subject=ContractSubject.THRESHOLD,
            )
    if not record.path.is_file() or checksum_file(record.path) != record.checksum:
        raise ArtifactIntegrityError("evaluation score artifact is incomplete or changed")

    scores, labels, rows = _score_arrays(str(record.path))
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
    shrinkage_curve = (
        _shrinkage_curve_evaluations(request) if isinstance(request.threshold_result, ShrinkageThresholdResult) else ()
    )
    return EvaluationDiagnostics(
        conformal_coverage=conformal_coverage,
        threshold_estimation=threshold_estimation,
        communication=communication,
        alert_burden=_evaluate_alert_burden(request.traffic_rate_evidence, clients, coordinate),
        shrinkage_curve=shrinkage_curve,
        calibration_size_ablation=request.calibration_size_ablation,
        sample_efficiency=sample_efficiency_curve(threshold_estimation) if threshold_estimation else (),
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
                    false_positive_rate=Ratio(false_positive_rate.value),
                    evidence=evidence,
                )
            )
    return tuple(diagnostics)


def _evaluate_shrinkage_curve(
    request: FederatedEvaluationRequest,
) -> tuple[tuple[ClientMetricResult, ...], PopulationMetricResult]:
    curve = _shrinkage_curve_evaluations(request)
    local_endpoint = ShrinkageWeight(1.0)
    matches = tuple(item for item in curve if item.lambda_weight == local_endpoint)
    if len(matches) != 1:
        raise ScientificContractError(
            "fixed shrinkage evaluation requires the predeclared local endpoint lambda=1",
            subject=request.threshold_result.method
            if not isinstance(request.threshold_result, ThresholdUnavailableResult)
            else None,
        )
    return matches[0].clients, matches[0].population


def _shrinkage_curve_evaluations(request: FederatedEvaluationRequest) -> tuple[ShrinkageLambdaEvaluation, ...]:
    result = request.threshold_result
    if not isinstance(result, ShrinkageThresholdResult):
        raise ScientificContractError("shrinkage curve evaluation requires a shrinkage result")

    weight_to_assignments: dict[ShrinkageWeight, list[ThresholdAssignment]] = {w: [] for w in result.weights}
    for item in result.assignments:
        if item.lambda_weight in weight_to_assignments:
            weight_to_assignments[item.lambda_weight].append(ThresholdAssignment(item.client, item.blended_threshold))

    evaluations: list[ShrinkageLambdaEvaluation] = []
    for weight in result.weights:
        assignments = tuple(weight_to_assignments[weight])
        if not assignments:
            raise ScientificContractError(
                f"shrinkage lambda {weight.value} has no client assignments",
                subject=result.method,
            )

        assignment_map: dict[ClientIdentity, ThresholdValue] = {}
        for item in assignments:
            if item.client in assignment_map:
                raise ScientificContractError("threshold assignments cannot repeat a client")
            assignment_map[item.client] = item.threshold

        fallback_threshold = _deployment_fallback_threshold(assignments, result)

        clients = tuple(
            _evaluate_score_record(request, assignment_map, fallback_threshold, record)
            for record in sorted(request.score_manifest.evaluation_records, key=lambda item: item.scored_client)
        )
        evaluations.append(
            ShrinkageLambdaEvaluation(
                lambda_weight=weight,
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
        ):
            return result.assignments
        case ShrinkageThresholdResult():
            raise ScientificContractError(
                "multi-lambda shrinkage cannot flatten to one assignment set; use curve evaluation"
            )
        case ConformalThresholdResult():
            return tuple(ThresholdAssignment(item.client, item.threshold) for item in result.assignments)


def _deployment_fallback_threshold(
    assignments: tuple[ThresholdAssignment, ...],
    result: ThresholdConstructionResult,
) -> ThresholdValue | None:
    match result:
        case SharedThresholdResult() | PooledSharedQuantileResult() | SampleWeightedSharedThresholdResult():
            return result.shared_threshold
        case FederatedStatisticsThresholdResult():
            return result.matched_threshold
        case (
            LocalThresholdResult()
            | FamilyThresholdResult()
            | GroupedThresholdResult()
            | ConformalThresholdResult()
            | ShrinkageThresholdResult()
        ):
            if not assignments:
                return None
            return unweighted_mean(tuple(item.threshold for item in assignments))
        case ThresholdUnavailableResult():
            return None


def _score_arrays(
    path: str,
) -> tuple[tuple[ScoreValue, ...], tuple[PopulationOutcomeLabel, ...], tuple[StableRowId, ...]]:
    required = [
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    ]
    try:
        frame = pl.read_parquet(path, columns=required)
    except pl.exceptions.ColumnNotFoundError as err:
        raise ArtifactIntegrityError("evaluation score artifact has an invalid schema") from err

    data = frame.to_dict(as_series=False)
    return (
        tuple(ScoreValue(float(value)) for value in data[required[2]]),
        tuple(PopulationOutcomeLabel(str(value)) for value in data[required[1]]),
        tuple(StableRowId(str(value)) for value in data[required[0]]),
    )
