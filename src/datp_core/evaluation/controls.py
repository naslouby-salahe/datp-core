"""Machine-verifiable fixed-score controls for threshold-policy comparisons."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

import polars as pl

from datp_core.domain.enums import (
    ContractSubject,
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    ScoreFrameColumn,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    AbsoluteTolerance,
    Checksum,
    ScoreValue,
    ThresholdValue,
    floats_absolutely_close,
)
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.cohorts import (
    ClientEligibilityRecord,
    EvaluationCohortManifest,
    build_evaluation_cohort_manifest,
    client_partition_counts_from_scores,
)
from datp_core.evaluation.confusion import calculate_confusion_counts
from datp_core.evaluation.models import (
    ClientMetricResult,
    MetricAvailability,
    MetricStatus,
    metric_by_id,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.capabilities import population_capabilities
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.protocols.inference import (
    FixedScoreInvariant,
    ScoreArtifactManifest,
    ScoreRecord,
)

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]

_LENGTH_PREFIX_BYTES = 8
_CALIBRATION_ROLES = frozenset((PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION))


class ClientChecksumField(StrEnum):
    EVALUATION_LABEL = "evaluation_label_checksum"
    SOURCE_ROW = "source_row_checksum"


@dataclass(frozen=True, slots=True)
class ClientAurocEvidence:
    client: ClientIdentity
    outcome: MetricAvailability

    def __post_init__(self) -> None:
        if self.outcome.metric is not MetricId.AUROC:
            raise ValueError("AUROC evidence must carry the AUROC metric")


@dataclass(frozen=True, slots=True)
class FixedScoreEvidence:
    """Checksummed evidence which must be invariant across threshold methods."""

    coordinate: FederatedTrainingCoordinate
    threshold_method: FederatedThresholdMethod
    calibration_role: PartitionRole
    model_checksum: Checksum
    preprocessing_checksum: Checksum
    selected_checkpoint_checksum: Checksum
    calibration_score_checksum: Checksum
    evaluation_score_checksum: Checksum
    evaluation_label_checksum: Checksum
    client_population_checksum: Checksum
    eligibility_cohort_checksum: Checksum
    source_row_checksum: Checksum
    score_order_checksum: Checksum
    aurocs: tuple[ClientAurocEvidence, ...]

    def __post_init__(self) -> None:
        if self.calibration_role not in _CALIBRATION_ROLES:
            raise ValueError("fixed-score evidence requires a calibration partition role")
        clients = tuple(item.client for item in self.aurocs)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("AUROC evidence must be unique by client")


@dataclass(frozen=True, slots=True)
class FederatedEvaluationInputs:
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreColumnChecksum:
    client: ClientIdentity
    checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientEvidenceChecksum:
    client: ClientIdentity
    checksum: Checksum


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
    calibration_records = score_manifest.records_for(calibration_role)
    if not calibration_records:
        raise ScientificContractError(
            "evaluation inputs require the declared calibration score set",
            subject=calibration_role,
        )
    cohort = build_evaluation_cohort_manifest(
        population=score_manifest.coordinate.population,
        partition_seed=score_manifest.coordinate.training_seed,
        client_counts=client_partition_counts_from_scores(score_manifest),
    )
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    return FederatedEvaluationInputs(
        cohort=cohort,
        fixed_score_evidence=FixedScoreEvidence(
            coordinate=score_manifest.coordinate,
            threshold_method=threshold_method,
            calibration_role=calibration_role,
            model_checksum=score_manifest.checkpoint_checksum,
            preprocessing_checksum=score_manifest.preprocessing_state_set_checksum,
            selected_checkpoint_checksum=score_manifest.checkpoint_checksum,
            calibration_score_checksum=score_manifest.score_set_checksum(calibration_role),
            evaluation_score_checksum=invariant.evaluation_score_set_checksum,
            evaluation_label_checksum=_evaluation_label_checksum(score_manifest),
            client_population_checksum=_client_population_checksum(score_manifest),
            eligibility_cohort_checksum=canonical_checksum(cohort),
            source_row_checksum=_evaluation_row_checksum(score_manifest),
            score_order_checksum=_score_order_checksum(score_manifest),
            aurocs=_client_aurocs(score_manifest, cohort),
        ),
    )


def evaluation_label_checksum(
    labels: Sequence[PopulationOutcomeLabel],
) -> Checksum:
    return _ordered_text_checksum(tuple(label.value for label in labels))


def source_row_checksum(rows: Sequence[str]) -> Checksum:
    return _ordered_text_checksum(tuple(rows))


def validate_evaluation_evidence(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    invariant = FixedScoreInvariant.from_manifest(manifest)
    _validate_evidence_manifest_binding(evidence, manifest, invariant)
    _validate_evidence_cohort_binding(evidence, cohort, clients)
    _validate_evidence_held_out_rows(evidence, manifest, clients)
    _validate_evidence_aurocs(evidence, clients)


def validate_fixed_score_controls(
    first: FixedScoreEvidence,
    second: FixedScoreEvidence,
    *,
    auroc_absolute_tolerance: AbsoluteTolerance,
) -> None:
    """Reject every changed fixed input; threshold policy is the sole difference."""
    if first.threshold_method is second.threshold_method:
        raise ScientificContractError(
            "fixed-score comparison requires distinct threshold methods",
            subject=ContractSubject.THRESHOLD_METHOD,
        )
    bindings = (
        (
            first.coordinate,
            second.coordinate,
            ContractSubject.COORDINATE,
            "training coordinate",
        ),
        (
            first.calibration_role,
            second.calibration_role,
            ContractSubject.SPLIT,
            "calibration partition role",
        ),
        (
            first.model_checksum,
            second.model_checksum,
            ContractSubject.SCORES,
            "model checksum",
        ),
        (
            first.preprocessing_checksum,
            second.preprocessing_checksum,
            ContractSubject.PREPROCESSING,
            "preprocessing checksum",
        ),
        (
            first.selected_checkpoint_checksum,
            second.selected_checkpoint_checksum,
            ContractSubject.CHECKPOINT_CANDIDATES,
            "selected-checkpoint checksum",
        ),
        (
            first.calibration_score_checksum,
            second.calibration_score_checksum,
            ContractSubject.SCORES,
            "calibration-score checksum",
        ),
        (
            first.evaluation_score_checksum,
            second.evaluation_score_checksum,
            ContractSubject.SCORES,
            "evaluation-score checksum",
        ),
        (
            first.evaluation_label_checksum,
            second.evaluation_label_checksum,
            ContractSubject.LABEL,
            "evaluation-label checksum",
        ),
        (
            first.client_population_checksum,
            second.client_population_checksum,
            ContractSubject.CLIENT_IDENTITY,
            "client population",
        ),
        (
            first.eligibility_cohort_checksum,
            second.eligibility_cohort_checksum,
            ContractSubject.CLIENT_IDENTITY,
            "eligibility cohort",
        ),
        (
            first.source_row_checksum,
            second.source_row_checksum,
            ContractSubject.ROWS,
            "source-row identities",
        ),
        (
            first.score_order_checksum,
            second.score_order_checksum,
            ContractSubject.SCORES,
            "score ordering",
        ),
    )
    for left, right, subject, name in bindings:
        _require_equal(left, right, subject, name)
    _require_auroc_invariance(
        first.aurocs,
        second.aurocs,
        auroc_absolute_tolerance,
    )


def _client_population_checksum(
    manifest: FederatedScoreArtifactManifest,
) -> Checksum:
    return canonical_checksum(tuple(sorted(record.scored_client for record in manifest.evaluation_records)))


def _evaluation_label_checksum(
    manifest: FederatedScoreArtifactManifest,
) -> Checksum:
    return _aggregate_score_record_checksum(
        manifest.evaluation_records,
        ScoreFrameColumn.OUTCOME_LABEL,
    )


def _evaluation_row_checksum(
    manifest: FederatedScoreArtifactManifest,
) -> Checksum:
    return _aggregate_score_record_checksum(
        manifest.evaluation_records,
        ScoreFrameColumn.STABLE_ROW_ID,
    )


def _aggregate_score_record_checksum(
    records: tuple[FederatedScoreRecord, ...],
    column: ScoreFrameColumn,
) -> Checksum:
    return canonical_checksum(
        tuple(
            ScoreColumnChecksum(
                client=record.scored_client,
                checksum=_score_column_checksum(record, column),
            )
            for record in sorted(
                records,
                key=lambda item: item.scored_client,
            )
        )
    )


def _score_column_checksum(
    record: FederatedScoreRecord,
    column: ScoreFrameColumn,
) -> Checksum:
    values = pl.read_parquet(record.path)[column.value].to_list()
    return _ordered_text_checksum(tuple(str(value) for value in values))


def _score_order_checksum(
    manifest: FederatedScoreArtifactManifest,
) -> Checksum:
    return canonical_checksum(
        tuple(
            ScoreColumnChecksum(
                client=record.scored_client,
                checksum=_score_column_checksum(
                    record,
                    ScoreFrameColumn.RECONSTRUCTION_ERROR,
                ),
            )
            for record in sorted(
                manifest.evaluation_records,
                key=lambda item: item.scored_client,
            )
        )
    )


def _client_aurocs(
    manifest: FederatedScoreArtifactManifest,
    cohort: EvaluationCohortManifest,
) -> tuple[ClientAurocEvidence, ...]:
    eligibility = tuple(sorted(cohort.records, key=lambda record: record.client))
    records = tuple(
        sorted(
            manifest.evaluation_records,
            key=lambda record: record.scored_client,
        )
    )
    if tuple(record.client for record in eligibility) != tuple(record.scored_client for record in records):
        raise ScientificContractError("evaluation inputs require cohort coverage for every score client")
    evidence_role = population_capabilities(manifest.coordinate.population).evidentiary_role
    return tuple(
        _client_auroc_evidence(
            manifest.coordinate,
            score_record,
            eligibility_record,
            evidence_role,
        )
        for score_record, eligibility_record in zip(
            records,
            eligibility,
            strict=True,
        )
    )


def _client_auroc_evidence(
    coordinate: FederatedTrainingCoordinate,
    record: FederatedScoreRecord,
    eligibility: ClientEligibilityRecord,
    evidence_role: EvidenceRole,
) -> ClientAurocEvidence:
    frame = pl.read_parquet(record.path)
    scores = tuple(ScoreValue(float(value)) for value in frame[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list())
    labels = tuple(
        PopulationOutcomeLabel(str(value)) for value in frame[ScoreFrameColumn.OUTCOME_LABEL.value].to_list()
    )
    rows = tuple(str(value) for value in frame[ScoreFrameColumn.STABLE_ROW_ID.value].to_list())
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
        metrics=calculate_client_metrics(
            confusion=confusion,
            scores=scores,
            labels=labels,
        ),
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


def _validate_evidence_manifest_binding(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    invariant: FixedScoreInvariant,
) -> None:
    if evidence.coordinate != manifest.coordinate:
        raise ScientificContractError("fixed-score evidence must match the score coordinate")
    calibration_records = manifest.records_for(evidence.calibration_role)
    if not calibration_records:
        raise ScientificContractError("fixed-score evidence calibration partition is unavailable in the score manifest")
    bindings = (
        ("model", evidence.model_checksum, invariant.model_checksum),
        (
            "preprocessing",
            evidence.preprocessing_checksum,
            invariant.preprocessing_state_set_checksum,
        ),
        (
            "checkpoint",
            evidence.selected_checkpoint_checksum,
            manifest.checkpoint_checksum,
        ),
        (
            "calibration score",
            evidence.calibration_score_checksum,
            manifest.score_set_checksum(evidence.calibration_role),
        ),
        (
            "evaluation score",
            evidence.evaluation_score_checksum,
            invariant.evaluation_score_set_checksum,
        ),
    )
    for name, observed, expected in bindings:
        if observed != expected:
            raise ScientificContractError(f"fixed-score evidence {name} checksum does not match the score manifest")


def _validate_evidence_cohort_binding(
    evidence: FixedScoreEvidence,
    cohort: EvaluationCohortManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    expected_population = canonical_checksum(tuple(sorted(client.client for client in clients)))
    if evidence.client_population_checksum != expected_population:
        raise ScientificContractError("fixed-score evidence client population checksum does not match evaluation")
    if evidence.eligibility_cohort_checksum != canonical_checksum(cohort):
        raise ScientificContractError("fixed-score evidence eligibility cohort checksum does not match evaluation")


def _validate_evidence_held_out_rows(
    evidence: FixedScoreEvidence,
    manifest: FederatedScoreArtifactManifest,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    if evidence.score_order_checksum != _score_order_checksum(manifest):
        raise ScientificContractError("fixed-score evidence score ordering checksum does not match evaluation")
    expected_labels = _aggregate_client_checksum(
        clients,
        ClientChecksumField.EVALUATION_LABEL,
    )
    expected_rows = _aggregate_client_checksum(
        clients,
        ClientChecksumField.SOURCE_ROW,
    )
    if evidence.evaluation_label_checksum != expected_labels or evidence.source_row_checksum != expected_rows:
        raise ScientificContractError("fixed-score evidence label or source-row checksum does not match evaluation")


def _validate_evidence_aurocs(
    evidence: FixedScoreEvidence,
    clients: tuple[ClientMetricResult, ...],
) -> None:
    observed = tuple(
        (
            client.client,
            metric_by_id(client.metrics, MetricId.AUROC),
        )
        for client in clients
    )
    if tuple(item.client for item in evidence.aurocs) != tuple(client for client, _outcome in observed):
        raise ScientificContractError("fixed-score AUROC evidence client order does not match evaluation")
    for expected_item, (_client, observed_outcome) in zip(
        evidence.aurocs,
        observed,
        strict=True,
    ):
        _require_matching_auroc(expected_item.outcome, observed_outcome)


def _aggregate_client_checksum(
    clients: tuple[ClientMetricResult, ...],
    field: ClientChecksumField,
) -> Checksum:
    entries = tuple(
        ClientEvidenceChecksum(
            client=item.client,
            checksum=(
                item.evaluation_label_checksum
                if field is ClientChecksumField.EVALUATION_LABEL
                else item.source_row_checksum
            ),
        )
        for item in sorted(clients, key=lambda result: result.client)
    )
    return canonical_checksum(entries)


def _ordered_text_checksum(values: Sequence[str]) -> Checksum:
    digest = sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(
            len(encoded).to_bytes(
                _LENGTH_PREFIX_BYTES,
                byteorder="big",
                signed=False,
            )
        )
        digest.update(encoded)
    return Checksum(digest.hexdigest())


def _require_equal(
    left: object,
    right: object,
    subject: ContractSubject,
    name: str,
) -> None:
    if left != right:
        raise ScientificContractError(
            f"fixed-score control failed: {name} differs",
            subject=subject,
        )


def _require_auroc_invariance(
    first: tuple[ClientAurocEvidence, ...],
    second: tuple[ClientAurocEvidence, ...],
    tolerance: AbsoluteTolerance,
) -> None:
    if tuple(item.client for item in first) != tuple(item.client for item in second):
        raise ScientificContractError(
            "fixed-score control failed: AUROC clients differ",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    for left, right in zip(first, second, strict=True):
        if left.outcome.status is not right.outcome.status:
            raise ScientificContractError(
                "fixed-score control failed: AUROC availability differs",
                subject=ContractSubject.HELD_OUT_METRICS,
            )
        if left.outcome.status is not MetricStatus.AVAILABLE:
            if left.outcome != right.outcome:
                raise ScientificContractError(
                    "fixed-score control failed: AUROC unavailable outcome differs",
                    subject=ContractSubject.HELD_OUT_METRICS,
                )
            continue
        if left.outcome.value is None or right.outcome.value is None:
            raise RuntimeError("available AUROC evidence must contain values")
        if not floats_absolutely_close(
            left.outcome.value.value,
            right.outcome.value.value,
            tolerance.value,
        ):
            raise ScientificContractError(
                "fixed-score control failed: AUROC differs",
                subject=ContractSubject.HELD_OUT_METRICS,
            )


def _require_matching_auroc(
    expected: MetricAvailability,
    observed: MetricAvailability,
) -> None:
    if expected.status is not observed.status:
        raise ScientificContractError("fixed-score AUROC availability does not match held-out evaluation")
    if expected.status is MetricStatus.AVAILABLE:
        if expected.value is None or observed.value is None:
            raise RuntimeError("available AUROC evidence must contain values")
        if not floats_absolutely_close(
            expected.value.value,
            observed.value.value,
            NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value,
        ):
            raise ScientificContractError("fixed-score AUROC evidence does not match held-out evaluation")
    elif expected != observed:
        raise ScientificContractError("fixed-score AUROC unavailable outcome does not match held-out evaluation")
