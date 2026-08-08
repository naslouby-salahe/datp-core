import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.data.registry import population_capabilities
from datp_core.domain.enums import (
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    ScoreFrameColumn,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.identifiers import StableRowId
from datp_core.domain.values.ratios import ScoreValue, ThresholdValue
from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.evaluation.cohort.construction import assert_cohort_invariant_to_threshold_methods
from datp_core.evaluation.cohort.contracts import ClientEligibilityRecord, EvaluationCohortManifest
from datp_core.evaluation.cohort.evidence import client_partition_counts_from_scores
from datp_core.analysis.metrics.confusion import calculate_confusion_counts
from datp_core.evaluation.fixed_score.checksums import (
    client_population_checksum,
    evaluation_label_checksum,
    evaluation_label_set_checksum,
    evaluation_row_set_checksum,
    evaluation_score_order_checksum,
    source_row_checksum,
)
from datp_core.evaluation.fixed_score.contracts import (
    CalibrationEvidence,
    ClientAurocEvidence,
    DetectorEvidence,
    FederatedEvaluationInputs,
    FixedScoreEvidence,
    HeldOutEvaluationEvidence,
    PopulationEvidence,
)
from datp_core.analysis.metrics.models import ClientMetricResult, metric_by_id
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.detector.scoring.contracts import FixedScoreInvariant, ScoreArtifactManifest, ScoreRecord

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]

_CALIBRATION_ROLES = frozenset((PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION))


def build_federated_evaluation_inputs(
    score_manifest: FederatedScoreArtifactManifest,
    threshold_method: FederatedThresholdMethod,
    *,
    calibration_role: PartitionRole = PartitionRole.CALIBRATION,
) -> FederatedEvaluationInputs:
    if calibration_role not in _CALIBRATION_ROLES:
        raise ScientificContractError(
            "evaluation inputs require a calibration partition role",
            subject=calibration_role,
        )
    if not score_manifest.records_for(calibration_role):
        raise ScientificContractError(
            "evaluation inputs require the declared calibration score set",
            subject=calibration_role,
        )

    cohort = assert_cohort_invariant_to_threshold_methods(
        population=score_manifest.coordinate.population,
        partition_seed=score_manifest.coordinate.training_seed,
        client_counts=client_partition_counts_from_scores(score_manifest),
        methods=(threshold_method,),
    )
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    evidence = FixedScoreEvidence(
        threshold_method=threshold_method,
        detector=DetectorEvidence(
            coordinate=score_manifest.coordinate,
            model_checksum=invariant.model_checksum,
            preprocessing_checksum=invariant.preprocessing_state_set_checksum,
            selected_checkpoint_checksum=score_manifest.checkpoint_checksum,
        ),
        calibration=CalibrationEvidence(
            role=calibration_role,
            score_checksum=score_manifest.score_set_checksum(calibration_role),
        ),
        evaluation=HeldOutEvaluationEvidence(
            score_checksum=invariant.evaluation_score_set_checksum,
            label_checksum=evaluation_label_set_checksum(score_manifest),
            source_row_checksum=evaluation_row_set_checksum(score_manifest),
            score_order_checksum=evaluation_score_order_checksum(score_manifest),
            aurocs=_client_aurocs(score_manifest, cohort),
        ),
        population=PopulationEvidence(
            client_inventory_checksum=client_population_checksum(score_manifest),
            eligibility_cohort_checksum=canonical_checksum(cohort),
        ),
    )
    return FederatedEvaluationInputs(cohort=cohort, fixed_score_evidence=evidence)


def _client_aurocs(
    manifest: FederatedScoreArtifactManifest,
    cohort: EvaluationCohortManifest,
) -> tuple[ClientAurocEvidence, ...]:
    eligibility = sorted(cohort.records, key=lambda record: record.client)
    records = sorted(manifest.evaluation_records, key=lambda record: record.scored_client)

    if len(eligibility) != len(records):
        raise ScientificContractError("evaluation inputs require cohort coverage for every score client")

    evidence_role = population_capabilities(manifest.coordinate.population).evidentiary_role

    evidences: list[ClientAurocEvidence] = []
    for score_record, eligibility_record in zip(records, eligibility, strict=True):
        if score_record.scored_client != eligibility_record.client:
            raise ScientificContractError("evaluation inputs require cohort coverage for every score client")

        evidences.append(
            _client_auroc_evidence(
                manifest.coordinate,
                score_record,
                eligibility_record,
                evidence_role,
            )
        )

    return tuple(evidences)


def _client_auroc_evidence(
    coordinate: FederatedTrainingCoordinate,
    record: FederatedScoreRecord,
    eligibility: ClientEligibilityRecord,
    evidence_role: EvidenceRole,
) -> ClientAurocEvidence:
    required_cols = [
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.STABLE_ROW_ID.value,
    ]
    frame_dict = pl.read_parquet(record.path, columns=required_cols).to_dict(as_series=False)

    scores = tuple(ScoreValue(float(value)) for value in frame_dict[required_cols[0]])
    labels = tuple(PopulationOutcomeLabel(str(value)) for value in frame_dict[required_cols[1]])
    rows = tuple(StableRowId(str(value)) for value in frame_dict[required_cols[2]])

    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=rows,
        threshold=ThresholdValue(0.0),
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=eligibility.attack_evaluable,
    )
    result = ClientMetricResult(
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
        evaluation_label_checksum=evaluation_label_checksum(labels),
        source_row_checksum=source_row_checksum(rows),
    )
    return ClientAurocEvidence(
        record.scored_client,
        metric_by_id(result.metrics, MetricId.AUROC),
    )
