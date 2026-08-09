"""Benign-only calibration eligibility decided before held-out evaluation."""

from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    LeakageError,
    ScientificContractError,
    require_contract,
)
from datp_core.core.identifiers import ContractSubject, PartitionRole, ScoreFrameColumn, StableRowId
from datp_core.core.numeric import CalibrationSize, RowCount, ScoreValue
from datp_core.data.populations.contracts import ClientIdentity, EligibleCohort, PopulationOutcomeLabel
from datp_core.data.populations.integrity import reject_non_benign_labels
from datp_core.detector.scoring.contracts import FederatedScoreRecord
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.protocols import CalibrationEligibilityProtocol


class CalibrationUnavailableReason(StrEnum):
    INSUFFICIENT_BENIGN_SUPPORT = "insufficient_benign_support"
    CALIBRATION_SIZE_EXCEEDS_SOURCE = "calibration_size_exceeds_source"


class EligibilityStatus(StrEnum):
    CANDIDATE = "candidate"
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class CalibrationSupport:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    benign_calibration_count: RowCount
    calibration_score_set_checksum: Checksum


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    support: CalibrationSupport
    minimum_support: CalibrationSize
    status: EligibilityStatus
    reason: CalibrationUnavailableReason | None

    def __post_init__(self) -> None:
        if self.status is EligibilityStatus.ELIGIBLE:
            require_contract(
                self.minimum_support.fits_within(self.support.benign_calibration_count),
                ErrorMessage("eligible status requires benign calibration count to meet the minimum support"),
                ContractSubject.CALIBRATION,
            )
            require_contract(
                self.reason is None,
                ErrorMessage("eligible clients cannot carry an unavailability reason"),
                ContractSubject.CALIBRATION,
            )
        elif self.status is EligibilityStatus.EXCLUDED:
            require_contract(
                self.reason is not None,
                ErrorMessage("excluded clients require a typed unavailability reason"),
                ContractSubject.CALIBRATION,
            )

    @property
    def is_eligible(self) -> bool:
        return self.status is EligibilityStatus.ELIGIBLE


@dataclass(frozen=True, slots=True)
class CalibrationSampleReference:
    client: ClientIdentity
    stable_row_id: StableRowId
    score: ScoreValue


def reject_evaluation_partition_in_eligibility(partition_role: PartitionRole) -> None:
    if partition_role is not PartitionRole.CALIBRATION:
        raise LeakageError(
            ErrorMessage("calibration eligibility must be decided from calibration-partition scores only"),
            subject=partition_role,
        )


def reject_calibration_evaluation_overlap(
    calibration_stable_row_ids: frozenset[StableRowId],
    evaluation_stable_row_ids: frozenset[StableRowId],
) -> None:
    if not calibration_stable_row_ids.isdisjoint(evaluation_stable_row_ids):
        raise LeakageError(
            ErrorMessage("calibration and evaluation partitions must not share source rows"),
            subject=ContractSubject.CALIBRATION,
        )


def reject_score_coordinate_mismatch(records: tuple[FederatedScoreRecord, ...]) -> None:
    if not records:
        return
    reference = records[0].coordinate
    if any(record.coordinate != reference for record in records[1:]):
        raise ScientificContractError(
            ErrorMessage("calibration eligibility requires every score record to share one coordinate"),
            subject=ContractSubject.COORDINATE,
        )


def load_benign_calibration_references(
    record: FederatedScoreRecord,
    *,
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN,
) -> tuple[CalibrationSampleReference, ...]:
    reject_evaluation_partition_in_eligibility(record.partition_role)
    frame = pl.read_parquet(
        record.path,
        columns=[
            ScoreFrameColumn.OUTCOME_LABEL.value,
            ScoreFrameColumn.STABLE_ROW_ID.value,
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
        ],
    )
    id_column = frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value)
    if id_column.n_unique() != len(id_column):
        raise ScientificContractError(
            ErrorMessage("calibration score rows must have unique stable source-row identities"),
            subject=ContractSubject.CALIBRATION,
        )
    label_column = frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value)
    reject_non_benign_labels(
        tuple(PopulationOutcomeLabel(str(label)) for label in label_column.cast(pl.String).to_list()),
        message="attack-labelled rows cannot enter benign calibration construction",
        subject=ContractSubject.CALIBRATION,
        benign_label=benign_label,
    )
    row_ids = id_column.cast(pl.String).to_list()
    scores = frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).cast(pl.Float64).to_list()
    return tuple(
        CalibrationSampleReference(
            client=record.scored_client,
            stable_row_id=StableRowId(row_id),
            score=ScoreValue(score),
        )
        for row_id, score in zip(row_ids, scores, strict=True)
    )


def calibration_support(
    record: FederatedScoreRecord,
    references: tuple[CalibrationSampleReference, ...],
    calibration_score_set_checksum: Checksum,
) -> CalibrationSupport:
    return CalibrationSupport(
        client=record.scored_client,
        coordinate=record.coordinate,
        benign_calibration_count=RowCount(len(references)),
        calibration_score_set_checksum=calibration_score_set_checksum,
    )


def decide_eligibility(
    support: CalibrationSupport,
    protocol: CalibrationEligibilityProtocol,
) -> EligibilityDecision:
    meets_minimum = protocol.minimum_support.fits_within(support.benign_calibration_count)
    return EligibilityDecision(
        support=support,
        minimum_support=protocol.minimum_support,
        status=EligibilityStatus.ELIGIBLE if meets_minimum else EligibilityStatus.EXCLUDED,
        reason=None if meets_minimum else CalibrationUnavailableReason.INSUFFICIENT_BENIGN_SUPPORT,
    )


def eligible_clients(decisions: tuple[EligibilityDecision, ...]) -> EligibleCohort:
    return EligibleCohort(
        clients=tuple(sorted(decision.support.client for decision in decisions if decision.is_eligible))
    )


def require_common_eligible_cohort(cohorts: tuple[EligibleCohort, ...]) -> EligibleCohort:
    if not cohorts:
        raise ScientificContractError(
            ErrorMessage("at least one eligible cohort is required for comparison"),
            subject=ContractSubject.CALIBRATION,
        )
    reference = cohorts[0]
    if any(cohort != reference for cohort in cohorts[1:]):
        raise ScientificContractError(
            ErrorMessage("threshold methods compared within one score coordinate must share the same eligible cohort"),
            subject=ContractSubject.CALIBRATION,
        )
    return reference
