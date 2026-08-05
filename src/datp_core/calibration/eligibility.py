"""Benign-only calibration eligibility, decided before held-out evaluation."""

import polars as pl

from datp_core.calibration.models import (
    CalibrationSampleReference,
    CalibrationSupport,
    CalibrationUnavailableReason,
    EligibilityDecision,
    EligibilityStatus,
)
from datp_core.domain.enums import ContractSubject, PartitionRole, ScoreFrameColumn
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, RowCount, ScoreValue, StableRowId
from datp_core.populations.integrity import reject_non_benign_labels
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.protocols.inference import ScoreRecord
from datp_core.protocols.models import CalibrationEligibilityProtocol


def reject_evaluation_partition_in_eligibility(partition_role: PartitionRole) -> None:
    if partition_role is not PartitionRole.CALIBRATION:
        raise LeakageError(
            "calibration eligibility must be decided from calibration-partition scores only",
            subject=partition_role,
        )


def reject_calibration_evaluation_overlap(
    calibration_stable_row_ids: frozenset[str],
    evaluation_stable_row_ids: frozenset[str],
) -> None:
    if calibration_stable_row_ids & evaluation_stable_row_ids:
        raise LeakageError(
            "calibration and evaluation partitions must not share source rows",
            subject=ContractSubject.CALIBRATION,
        )


def reject_score_coordinate_mismatch(records: tuple[ScoreRecord, ...]) -> None:
    if len(frozenset(record.coordinate for record in records)) > 1:
        raise ScientificContractError(
            "calibration eligibility requires every score record to share one coordinate",
            subject=ContractSubject.COORDINATE,
        )


def load_benign_calibration_references(
    record: ScoreRecord,
    *,
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN,
) -> tuple[CalibrationSampleReference, ...]:
    reject_evaluation_partition_in_eligibility(record.partition_role)
    frame = pl.read_parquet(record.path)
    labels = tuple(str(value) for value in frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value).to_list())
    reject_non_benign_labels(
        labels,
        message="attack-labelled rows cannot enter benign calibration construction",
        subject=ContractSubject.CALIBRATION,
        benign_label=benign_label.value,
    )
    stable_row_ids = tuple(str(value) for value in frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).to_list())
    if len(set(stable_row_ids)) != len(stable_row_ids):
        raise ScientificContractError(
            "calibration score rows must have unique stable source-row identities",
            subject=ContractSubject.CALIBRATION,
        )
    scores = tuple(float(value) for value in frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_list())
    return tuple(
        CalibrationSampleReference(
            client=record.scored_client,
            stable_row_id=StableRowId(row_id),
            score=ScoreValue(score),
        )
        for row_id, score in zip(stable_row_ids, scores, strict=True)
    )


def calibration_support(
    record: ScoreRecord,
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
    meets_minimum = support.benign_calibration_count >= protocol.minimum_support
    return EligibilityDecision(
        support=support,
        minimum_support=protocol.minimum_support,
        status=EligibilityStatus.ELIGIBLE if meets_minimum else EligibilityStatus.EXCLUDED,
        reason=None if meets_minimum else CalibrationUnavailableReason.INSUFFICIENT_BENIGN_SUPPORT,
    )


def eligible_clients(decisions: tuple[EligibilityDecision, ...]) -> tuple[ClientIdentity, ...]:
    return tuple(sorted(decision.client for decision in decisions if decision.is_eligible))


def require_common_eligible_cohort(
    cohorts: tuple[tuple[ClientIdentity, ...], ...],
) -> tuple[ClientIdentity, ...]:
    if not cohorts:
        raise ScientificContractError(
            "at least one eligible cohort is required for comparison",
            subject=ContractSubject.CALIBRATION,
        )
    reference = frozenset(cohorts[0])
    if any(frozenset(cohort) != reference for cohort in cohorts[1:]):
        raise ScientificContractError(
            "threshold methods compared within one score coordinate must share the same eligible cohort",
            subject=ContractSubject.CALIBRATION,
        )
    return cohorts[0]
