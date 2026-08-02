"""Held-out federated evaluation over immutable scores and thresholds."""

from dataclasses import dataclass, fields
from enum import StrEnum
from json import dumps
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import (
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    PublicationStatus,
    ScoreFrameColumn,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    Checksum,
    CoverageTarget,
    MetricValue,
    RowCount,
    ScoreValue,
    ThresholdValue,
    checksum_file,
    checksum_text,
    floats_absolutely_close,
)
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.cohorts import (
    ClientEligibilityRecord,
    EvaluationCohortManifest,
    build_evaluation_cohort_manifest,
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
from datp_core.evaluation.controls import ClientAurocEvidence, FixedScoreEvidence, validate_fixed_score_controls
from datp_core.evaluation.models import (
    ClientMetricResult,
    MetricAvailability,
    MetricStatus,
    MetricWarning,
    PopulationMetricResult,
)
from datp_core.evaluation.models import (
    HeldOutBenignScore as ConformalHeldOutBenignScore,
)
from datp_core.evaluation.models import (
    HeldOutBenignScore as ThresholdEstimationHeldOutBenignScore,
)
from datp_core.evaluation.operational import AlertBurdenDiagnostic, calculate_alert_burden
from datp_core.evaluation.population_metrics import calculate_population_metrics
from datp_core.evaluation.threshold_estimation import (
    ThresholdEstimationDiagnostic,
    ThresholdEstimationProvenance,
    evaluate_threshold_estimate,
)
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.capabilities import population_capabilities
from datp_core.populations.models import ClientIdentity, ClientPartitionCounts, PopulationOutcomeLabel
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE
from datp_core.scoring.models import FixedScoreInvariant, ScoreArtifactManifest, ScoreRecord
from datp_core.thresholding.models import (
    ConformalAssignment,
    ConformalThresholdResult,
    FamilyThresholdResult,
    FederatedStatisticsThresholdResult,
    GroupedThresholdResult,
    LocalThresholdResult,
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
    ShrinkageThresholdResult,
    ThresholdAssignment,
    ThresholdConstructionResult,
    ThresholdUnavailableResult,
)


class FederatedEvaluationAssetName(StrEnum):
    DOCUMENT = "federated_evaluation.json"
    COMPLETE = "COMPLETE"


def _serialize(obj):  # noqa: C901, PLR0911
    """Serialize domain value objects, enums, dataclasses, and tuples to JSON-compatible primitives."""
    if obj is None:
        return None
    if isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, tuple):
        return tuple(_serialize(item) for item in obj)
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dataclass_fields__"):
        own_fields = fields(obj)
        if len(own_fields) == 1 and own_fields[0].name == "value":
            return obj.value
        return {field.name: _serialize(getattr(obj, field.name)) for field in own_fields}
    raise TypeError(f"cannot serialize {type(obj)}")


@dataclass(frozen=True, slots=True)
class ConformalCoverageStageInput:
    assignment: ConformalAssignment
    target_coverage: CoverageTarget
    held_out_benign_scores: tuple[ConformalHeldOutBenignScore, ...]


@dataclass(frozen=True, slots=True)
class ThresholdEstimationStageInput:
    provenance: ThresholdEstimationProvenance
    estimated_threshold: ThresholdValue
    exact_pooled_benign_quantile_reference: ThresholdValue
    held_out_benign_scores: tuple[ThresholdEstimationHeldOutBenignScore, ...]


@dataclass(frozen=True, slots=True)
class EvaluationDiagnostics:
    conformal_coverage: tuple[ConformalCoverageDiagnostic, ...]
    threshold_estimation: tuple[ThresholdEstimationDiagnostic, ...]
    communication: CommunicationDiagnostic | None
    alert_burden: tuple[AlertBurdenDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class FederatedEvaluationInputs:
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence


@dataclass(frozen=True, slots=True)
class EvaluateFederatedRequest:
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
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None = None
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(frozen=True, slots=True)
class FederatedEvaluationResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum


def _validate_temporal_provenance(request: EvaluateFederatedRequest) -> None:
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


def evaluate_federated_stage(request: EvaluateFederatedRequest) -> FederatedEvaluationResult:
    """Evaluate pre-existing scores only; this stage cannot train, rescore, or calibrate."""
    _validate_temporal_provenance(request)
    clients, population = _evaluate(request)
    diagnostics = _evaluate_diagnostics(request, clients)
    _validate_evaluation_evidence(request.fixed_score_evidence, request.score_manifest, request.cohort, clients)
    if request.comparison_fixed_score_evidence is not None:
        validate_fixed_score_controls(
            request.fixed_score_evidence,
            request.comparison_fixed_score_evidence,
            auroc_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE.value,
        )
    document = _evaluation_payload(request, clients, population, diagnostics)
    payload = dumps(document, indent=2, sort_keys=True) + "\n"
    digest = checksum_text(payload)

    def write(temporary: Path) -> None:
        (temporary / FederatedEvaluationAssetName.DOCUMENT).write_text(payload, encoding="utf-8")
        (temporary / FederatedEvaluationAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")

    publication = AtomicPublication(
        request.output_directory,
        request.overwrite,
        lambda directory: _is_reusable(directory, digest),
        write,
        rmtree,
    )
    reused = publish_atomically(publication)
    return FederatedEvaluationResult(
        stage=StageOperationId.EVALUATE_FEDERATED,
        publication_status=PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED,
        clients=clients,
        population=population,
        diagnostics=diagnostics,
        complete_digest=checksum_file(request.output_directory / FederatedEvaluationAssetName.COMPLETE),
    )


def _evaluate(request: EvaluateFederatedRequest) -> tuple[tuple[ClientMetricResult, ...], PopulationMetricResult]:
    manifest = request.score_manifest
    _validate_evaluation_request(request)
    assignments = _assignments(request.threshold_result)
    ordered = tuple(
        _evaluate_score_record(request, assignments, record)
        for record in sorted(manifest.evaluation_records, key=lambda item: item.scored_client.client_id)
    )
    return ordered, calculate_population_metrics(ordered)


def _validate_evaluation_request(request: EvaluateFederatedRequest) -> None:
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
    request: EvaluateFederatedRequest,
    assignments: tuple[ThresholdAssignment, ...],
    record: ScoreRecord,
) -> ClientMetricResult:
    threshold = _threshold_for_client(assignments, record.scored_client.client_id)
    eligibility = _cohort_record_for_client(request.cohort, record.scored_client.client_id)
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
        evaluation_label_checksum=checksum_text("|".join(label.value for label in labels)),
        source_row_checksum=checksum_text("|".join(rows)),
    )


def _evaluation_cohort(record: ClientEligibilityRecord) -> EvaluationCohort:
    if record.fpr_evaluable:
        return EvaluationCohort.FPR_EVALUABLE
    if record.deployment_fallback:
        return EvaluationCohort.DEPLOYMENT_FALLBACK
    return EvaluationCohort.UNAVAILABLE


def build_federated_evaluation_inputs(
    score_manifest: ScoreArtifactManifest,
    threshold_method: FederatedThresholdMethod,
) -> FederatedEvaluationInputs:
    """Derive cohort and fixed-score controls from unchanged federated score artifacts."""
    cohort = build_evaluation_cohort_manifest(
        population=score_manifest.coordinate.population,
        partition_seed=score_manifest.coordinate.training_seed,
        client_counts=_client_partition_counts(score_manifest),
    )
    return FederatedEvaluationInputs(
        cohort=cohort,
        fixed_score_evidence=FixedScoreEvidence(
            coordinate=score_manifest.coordinate,
            threshold_method=threshold_method,
            model_checksum=score_manifest.checkpoint_checksum,
            preprocessing_checksum=score_manifest.preprocessing_state_set_checksum,
            selected_checkpoint_checksum=score_manifest.checkpoint_checksum,
            calibration_score_checksum=FixedScoreInvariant.from_manifest(score_manifest).calibration_score_set_checksum,
            evaluation_score_checksum=FixedScoreInvariant.from_manifest(score_manifest).evaluation_score_set_checksum,
            evaluation_label_checksum=_evaluation_label_checksum(score_manifest),
            client_population_checksum=_client_population_checksum(score_manifest),
            eligibility_cohort_checksum=_cohort_checksum(cohort),
            source_row_checksum=_evaluation_row_checksum(score_manifest),
            score_order_checksum=_score_order_checksum(score_manifest),
            aurocs=_client_aurocs(score_manifest, cohort),
        ),
    )


def _client_partition_counts(manifest: ScoreArtifactManifest) -> tuple[ClientPartitionCounts, ...]:
    calibration = tuple(sorted(manifest.calibration_records, key=lambda item: item.scored_client.client_id))
    evaluation = tuple(sorted(manifest.evaluation_records, key=lambda item: item.scored_client.client_id))
    if tuple(record.scored_client for record in calibration) != tuple(record.scored_client for record in evaluation):
        raise ScientificContractError("evaluation inputs require matching calibration and evaluation score clients")
    return tuple(
        ClientPartitionCounts(
            client_id=calibration_record.scored_client.client_id,
            benign_calibration_count=_label_count(calibration_record, PopulationOutcomeLabel.BENIGN),
            benign_evaluation_count=_label_count(evaluation_record, PopulationOutcomeLabel.BENIGN),
            attack_evaluation_count=_label_count(evaluation_record, PopulationOutcomeLabel.ATTACK),
            accepted=True,
            deployment_fallback=False,
        )
        for calibration_record, evaluation_record in zip(calibration, evaluation, strict=True)
    )


def _label_count(record: ScoreRecord, label: PopulationOutcomeLabel) -> RowCount:
    frame = pl.read_parquet(record.path)
    return RowCount(int((frame[ScoreFrameColumn.OUTCOME_LABEL.value] == label.value).sum()))


def _client_population_checksum(manifest: ScoreArtifactManifest) -> Checksum:
    return checksum_text("|".join(sorted(record.scored_client.client_id for record in manifest.evaluation_records)))


def _cohort_checksum(cohort: EvaluationCohortManifest) -> Checksum:
    return checksum_text(
        "|".join(
            f"{record.client_id}:{record.calibration_eligible}:{record.fpr_evaluable}:"
            f"{record.attack_evaluable}:{record.deployment_fallback}"
            for record in sorted(cohort.records, key=lambda item: item.client_id)
        )
    )


def _evaluation_label_checksum(manifest: ScoreArtifactManifest) -> Checksum:
    return _aggregate_score_record_checksum(manifest.evaluation_records, ScoreFrameColumn.OUTCOME_LABEL)


def _evaluation_row_checksum(manifest: ScoreArtifactManifest) -> Checksum:
    return _aggregate_score_record_checksum(manifest.evaluation_records, ScoreFrameColumn.STABLE_ROW_ID)


def _aggregate_score_record_checksum(records: tuple[ScoreRecord, ...], column: ScoreFrameColumn) -> Checksum:
    pairs = tuple(
        sorted(
            (
                record.scored_client.client_id,
                _score_column_checksum(record, column).value,
            )
            for record in records
        )
    )
    return checksum_text("|".join(f"{client}:{checksum}" for client, checksum in pairs))


def _score_column_checksum(record: ScoreRecord, column: ScoreFrameColumn) -> Checksum:
    values = pl.read_parquet(record.path)[column.value].to_list()
    return checksum_text("|".join(str(value) for value in values))


def _client_aurocs(
    manifest: ScoreArtifactManifest, cohort: EvaluationCohortManifest
) -> tuple[ClientAurocEvidence, ...]:
    eligibility = tuple(sorted(cohort.records, key=lambda item: item.client_id))
    records = tuple(sorted(manifest.evaluation_records, key=lambda item: item.scored_client.client_id))
    if tuple(item.client_id for item in eligibility) != tuple(record.scored_client.client_id for record in records):
        raise ScientificContractError("evaluation inputs require cohort coverage for every score client")
    return tuple(
        _client_auroc_evidence(
            manifest.coordinate,
            record,
            eligibility_record,
            population_capabilities(manifest.coordinate.population).evidentiary_role,
        )
        for record, eligibility_record in zip(records, eligibility, strict=True)
    )


def _client_auroc_evidence(
    coordinate: FederatedTrainingCoordinate,
    record: ScoreRecord,
    eligibility: ClientEligibilityRecord,
    evidence_role: EvidenceRole,
) -> ClientAurocEvidence:
    scores, labels, rows = _score_arrays(pl.read_parquet(record.path))
    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=rows,
        threshold=ThresholdValue(0.0),
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=eligibility.attack_evaluable,
    )
    auroc = _metric_availability(
        ClientMetricResult(
            coordinate=coordinate,
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            client=record.scored_client,
            cohort=EvaluationCohort.FPR_EVALUABLE,
            threshold=ThresholdValue(0.0),
            confusion=confusion,
            metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
            warnings=(),
            evidence_role=evidence_role,
            evaluation_score_checksum=record.checksum,
            evaluation_label_checksum=checksum_text("|".join(label.value for label in labels)),
            source_row_checksum=checksum_text("|".join(rows)),
        ),
        MetricId.AUROC,
    )
    return ClientAurocEvidence(record.scored_client, auroc)


def _evaluate_diagnostics(
    request: EvaluateFederatedRequest, clients: tuple[ClientMetricResult, ...]
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
    alert_burden = _evaluate_alert_burden(request.traffic_rate_evidence, clients, coordinate)
    return EvaluationDiagnostics(conformal_coverage, threshold_estimation, communication, alert_burden)


def _evaluate_threshold_estimation_input(
    diagnostic: ThresholdEstimationStageInput, coordinate: FederatedTrainingCoordinate
) -> ThresholdEstimationDiagnostic:
    if diagnostic.provenance.coordinate != coordinate:
        raise ScientificContractError("threshold-estimation diagnostics must use the evaluated score coordinate")
    return evaluate_threshold_estimate(
        provenance=diagnostic.provenance,
        estimated_threshold=diagnostic.estimated_threshold,
        exact_pooled_benign_quantile_reference=diagnostic.exact_pooled_benign_quantile_reference,
        held_out_benign_scores=diagnostic.held_out_benign_scores,
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
        false_positive_rate = _metric_value(client, MetricId.FALSE_POSITIVE_RATE)
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


def _evaluation_payload(
    request: EvaluateFederatedRequest,
    clients: tuple[ClientMetricResult, ...],
    population: PopulationMetricResult,
    diagnostics: EvaluationDiagnostics,
):
    manifest = request.score_manifest
    return _serialize(
        {
            "stage": StageOperationId.EVALUATE_FEDERATED,
            "score_coordinate": manifest.coordinate,
            "score_checkpoint_checksum": manifest.checkpoint_checksum,
            "preprocessing_state_set_checksum": manifest.preprocessing_state_set_checksum,
            "split_manifest_checksum": manifest.split_manifest_checksum,
            "threshold_method": request.threshold_result.method,
            "evidence_role": request.evidence_role,
            "fixed_score_evidence": request.fixed_score_evidence,
            "cohort": request.cohort,
            "clients": tuple(_client_payload(client) for client in clients),
            "population": _population_payload(population),
            "conformal_coverage": diagnostics.conformal_coverage,
            "threshold_estimation": diagnostics.threshold_estimation,
            "communication": diagnostics.communication,
            "alert_burden": diagnostics.alert_burden,
            "temporal_provenance": request.temporal_provenance,
        }
    )


def _client_payload(result: ClientMetricResult) -> dict:
    return {
        "coordinate": result.coordinate,
        "threshold_method": result.threshold_method,
        "client": result.client,
        "cohort": result.cohort,
        "threshold": result.threshold,
        "confusion": result.confusion,
        "metrics": tuple(_metric_payload(metric) for metric in result.metrics),
        "warnings": tuple(_warning_payload(warning) for warning in result.warnings),
        "evidence_role": result.evidence_role,
        "evaluation_score_checksum": result.evaluation_score_checksum,
        "evaluation_label_checksum": result.evaluation_label_checksum,
        "source_row_checksum": result.source_row_checksum,
    }


def _population_payload(result: PopulationMetricResult) -> dict:
    return {
        "coordinate": result.coordinate,
        "threshold_method": result.threshold_method,
        "cohort": result.cohort,
        "metrics": tuple(_metric_payload(metric) for metric in result.metrics),
        "candidate_client_count": result.candidate_client_count,
        "calibration_eligible_client_count": result.calibration_eligible_client_count,
        "fpr_evaluable_client_count": result.fpr_evaluable_client_count,
        "attack_evaluable_client_count": result.attack_evaluable_client_count,
        "deployment_fallback_count": result.deployment_fallback_count,
        "unavailable_client_count": result.unavailable_client_count,
        "excluded_clients": result.excluded_clients,
        "warnings": tuple(_warning_payload(warning) for warning in result.warnings),
        "evidence_role": result.evidence_role,
    }


def _metric_payload(result: MetricAvailability) -> dict:
    return {
        "metric": result.metric,
        "status": result.status,
        "value": result.value,
        "denominator": result.denominator,
        "unavailable_reason": None if result.outcome is None else result.outcome.reason,
    }


def _warning_payload(warning: MetricWarning) -> dict:
    return {"code": warning.code, "metric": warning.metric, "client": warning.client}


def _validate_evaluation_evidence(
    evidence: FixedScoreEvidence,
    manifest: ScoreArtifactManifest,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    invariant = FixedScoreInvariant.from_manifest(manifest)
    _validate_evidence_manifest_binding(evidence, manifest, invariant)
    _validate_evidence_cohort_binding(evidence, cohort, clients)
    _validate_evidence_held_out_rows(evidence, manifest, clients)
    _validate_evidence_aurocs(evidence, clients)


def _validate_evidence_manifest_binding(
    evidence: FixedScoreEvidence,
    manifest: ScoreArtifactManifest,
    invariant: FixedScoreInvariant,
) -> None:
    if evidence.coordinate != manifest.coordinate:
        raise ScientificContractError("fixed-score evidence must match the score coordinate")
    _require_manifest_checksums(
        (
            ("model", evidence.model_checksum, invariant.model_checksum),
            ("preprocessing", evidence.preprocessing_checksum, invariant.preprocessing_state_set_checksum),
            ("checkpoint", evidence.selected_checkpoint_checksum, manifest.checkpoint_checksum),
            ("calibration score", evidence.calibration_score_checksum, invariant.calibration_score_set_checksum),
            ("evaluation score", evidence.evaluation_score_checksum, invariant.evaluation_score_set_checksum),
        )
    )


def _require_manifest_checksums(bindings: tuple[tuple[str, Checksum, Checksum], ...]) -> None:
    for name, observed, expected in bindings:
        if observed != expected:
            raise ScientificContractError(f"fixed-score evidence {name} checksum does not match the score manifest")


def _validate_evidence_cohort_binding(
    evidence: FixedScoreEvidence,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    client_ids = tuple(sorted(client.client.client_id for client in clients))
    expected_population = checksum_text("|".join(client_ids))
    if evidence.client_population_checksum != expected_population:
        raise ScientificContractError("fixed-score evidence client population checksum does not match evaluation")
    expected_cohort = checksum_text(
        "|".join(
            f"{record.client_id}:{record.calibration_eligible}:{record.fpr_evaluable}:"
            f"{record.attack_evaluable}:{record.deployment_fallback}"
            for record in sorted(cohort.records, key=lambda item: item.client_id)
        )
    )
    if evidence.eligibility_cohort_checksum != expected_cohort:
        raise ScientificContractError("fixed-score evidence eligibility cohort checksum does not match evaluation")


def _validate_evidence_held_out_rows(
    evidence: FixedScoreEvidence,
    manifest: ScoreArtifactManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    if evidence.score_order_checksum != _score_order_checksum(manifest):
        raise ScientificContractError("fixed-score evidence score ordering checksum does not match evaluation")
    expected_labels = _aggregate_client_checksum(clients, "evaluation_label_checksum")
    expected_rows = _aggregate_client_checksum(clients, "source_row_checksum")
    if evidence.evaluation_label_checksum != expected_labels or evidence.source_row_checksum != expected_rows:
        raise ScientificContractError("fixed-score evidence label or source-row checksum does not match evaluation")


def _validate_evidence_aurocs(
    evidence: FixedScoreEvidence,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    observed_aurocs = tuple((client.client, _metric_availability(client, MetricId.AUROC)) for client in clients)
    _require_auroc_client_order(evidence.aurocs, observed_aurocs)
    _require_matching_aurocs(evidence.aurocs, observed_aurocs)


def _require_auroc_client_order(
    expected: tuple[ClientAurocEvidence, ...], observed: tuple[tuple[ClientIdentity, MetricAvailability], ...]
) -> None:
    if tuple(item.client for item in expected) != tuple(client for client, _ in observed):
        raise ScientificContractError("fixed-score AUROC evidence client order does not match evaluation")


def _require_matching_aurocs(
    expected: tuple[ClientAurocEvidence, ...], observed: tuple[tuple[ClientIdentity, MetricAvailability], ...]
) -> None:
    for expected_item, (_, observed_outcome) in zip(expected, observed, strict=True):
        _require_matching_auroc(expected_item.outcome, observed_outcome)


def _require_matching_auroc(expected: MetricAvailability, observed: MetricAvailability) -> None:
    if expected.status is not observed.status:
        raise ScientificContractError("fixed-score AUROC availability does not match held-out evaluation")
    if expected.status is MetricStatus.AVAILABLE:
        _require_matching_available_auroc(expected, observed)
        return
    if expected != observed:
        raise ScientificContractError("fixed-score AUROC unavailable outcome does not match held-out evaluation")


def _require_matching_available_auroc(expected: MetricAvailability, observed: MetricAvailability) -> None:
    if expected.value is None or observed.value is None:
        raise RuntimeError("available AUROC evidence must contain values")
    if not floats_absolutely_close(
        expected.value.value,
        observed.value.value,
        FIXED_SCORE_ABSOLUTE_TOLERANCE.value,
    ):
        raise ScientificContractError("fixed-score AUROC evidence does not match held-out evaluation")


def _aggregate_client_checksum(clients: tuple[ClientMetricResult, ...], field: str) -> Checksum:
    match field:
        case "evaluation_label_checksum":
            pairs = tuple(sorted((item.client.client_id, item.evaluation_label_checksum.value) for item in clients))
        case "source_row_checksum":
            pairs = tuple(sorted((item.client.client_id, item.source_row_checksum.value) for item in clients))
        case _:
            raise ValueError("unsupported client checksum field")
    return checksum_text("|".join(f"{client}:{value}" for client, value in pairs))


def _metric_value(result: ClientMetricResult, metric_id: MetricId) -> MetricValue | None:
    for metric in result.metrics:
        if metric.metric is metric_id:
            return metric.value
    raise ScientificContractError("client result is missing a required metric")


def _metric_availability(result: ClientMetricResult, metric_id: MetricId) -> MetricAvailability:
    for metric in result.metrics:
        if metric.metric is metric_id:
            return metric
    raise ScientificContractError("client result is missing a required metric")


def _score_order_checksum(manifest: ScoreArtifactManifest) -> Checksum:
    payloads: list[str] = []
    for record in sorted(manifest.evaluation_records, key=lambda item: item.scored_client.client_id):
        frame = pl.read_parquet(record.path)
        payloads.append(
            f"{record.scored_client.client_id}:"
            + "|".join(str(value) for value in frame[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list())
        )
    return checksum_text("\n".join(payloads))


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


def _threshold_for_client(assignments: tuple[ThresholdAssignment, ...], client_id: str) -> ThresholdValue | None:
    matches = tuple(item.threshold for item in assignments if item.client.client_id == client_id)
    if len(matches) > 1:
        raise ScientificContractError("threshold assignments cannot repeat a client")
    return matches[0] if matches else None


def _cohort_record_for_client(cohort: EvaluationCohortManifest, client_id: str) -> ClientEligibilityRecord | None:
    matches = tuple(record for record in cohort.records if record.client_id == client_id)
    if len(matches) > 1:
        raise ScientificContractError("evaluation cohort cannot repeat a client")
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


def _is_reusable(directory: Path, digest: Checksum) -> bool:
    complete = directory / FederatedEvaluationAssetName.COMPLETE
    document = directory / FederatedEvaluationAssetName.DOCUMENT
    if not complete.is_file() or not document.is_file():
        return False
    return complete.read_text(encoding="utf-8").strip() == digest.value
