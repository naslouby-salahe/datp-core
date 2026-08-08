"""Shared scoring and metric extraction for personalized training stress tests."""

from __future__ import annotations

import polars as pl

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    ContractSubject,
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    PartitionRole,
    ScoreFrameColumn,
    StableRowId,
)
from datp_core.core.numeric import ScoreValue
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.confusion import calculate_confusion_counts
from datp_core.evaluation.fixed_score.checksums import evaluation_label_checksum, source_row_checksum
from datp_core.evaluation.models import ClientMetricResult
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.pipeline.scoring.models import ClientScoringInput, FederatedScoreArtifactManifest, FederatedScoreRecord
from datp_core.preprocessing.models import ClientPreprocessingResult
from datp_core.thresholds.contracts import ThresholdAssignment


def client_scoring_input(
    publications: tuple[ClientPreprocessingResult, ...],
    client: ClientIdentity,
) -> ClientScoringInput:
    matches = tuple(item for item in publications if item.client_identity.value == client.client_id)
    if len(matches) != 1:
        raise ScientificContractError(f"expected one preprocessing publication for {client.client_id}")
    publication = matches[0]
    return ClientScoringInput(
        client=client,
        calibration_features=pl.read_parquet(publication.paths.calibration),
        evaluation_features=pl.read_parquet(publication.paths.evaluation),
    )


def client_metric(
    coordinate: FederatedTrainingCoordinate,
    threshold_method: FederatedThresholdMethod,
    manifest: FederatedScoreArtifactManifest,
    assignment: ThresholdAssignment,
    cohort_manifest: EvaluationCohortManifest,
) -> ClientMetricResult:
    record = score_record_for_client(manifest.evaluation_records, assignment.client, PartitionRole.EVALUATION)
    frame = pl.read_parquet(record.path)
    scores = tuple(ScoreValue(float(value)) for value in frame[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list())
    labels = tuple(
        PopulationOutcomeLabel(str(value)) for value in frame[ScoreFrameColumn.OUTCOME_LABEL.value].to_list()
    )
    rows = tuple(StableRowId(str(value)) for value in frame[ScoreFrameColumn.STABLE_ROW_ID.value].to_list())
    eligibility_matches = tuple(item for item in cohort_manifest.records if item.client == assignment.client)
    if len(eligibility_matches) != 1:
        raise ScientificContractError(
            f"expected one evaluation-cohort record for {assignment.client.client_id}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    eligibility = eligibility_matches[0]
    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=rows,
        threshold=assignment.threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=eligibility.attack_evaluable,
    )
    if eligibility.fpr_evaluable:
        cohort = EvaluationCohort.FPR_EVALUABLE
    elif eligibility.deployment_fallback:
        cohort = EvaluationCohort.DEPLOYMENT_FALLBACK
    else:
        cohort = EvaluationCohort.UNAVAILABLE
    return ClientMetricResult(
        coordinate=coordinate,
        threshold_method=threshold_method,
        cohort=cohort,
        client=assignment.client,
        threshold=assignment.threshold,
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
        evaluation_score_checksum=record.checksum,
        evaluation_label_checksum=evaluation_label_checksum(labels),
        source_row_checksum=source_row_checksum(rows),
    )


def score_record_for_client(
    records: tuple[FederatedScoreRecord, ...],
    client: ClientIdentity,
    role: PartitionRole,
) -> FederatedScoreRecord:
    matches = tuple(item for item in records if item.scored_client == client)
    if len(matches) != 1:
        raise ScientificContractError(
            f"expected one {role.value} score record for {client.client_id}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]
