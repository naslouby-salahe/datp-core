"""Benign-only calibration eligibility, decided before held-out evaluation."""

import polars as pl

from datp_core.calibration.models import (
    CalibrationSampleReference,
    CalibrationSupport,
    CalibrationUnavailableReason,
    EligibilityDecision,
    EligibilityStatus,
)
from datp_core.datasets.partitioning.contracts import EligibleCohort, PopulationOutcomeLabel
from datp_core.datasets.partitioning.integrity import reject_non_benign_labels
from datp_core.domain.enums import ContractSubject, PartitionRole, ScoreFrameColumn
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.identifiers import StableRowId
from datp_core.domain.values.ratios import ScoreValue
from datp_core.protocols.calibration import CalibrationEligibilityProtocol
from datp_core.protocols.inference import ScoreRecord


def reject_evaluation_partition_in_eligibility(partition_role: PartitionRole) -> None:
    if partition_role is not PartitionRole.CALIBRATION:
        raise LeakageError(
            "calibration eligibility must be decided from calibration-partition scores only",
            subject=partition_role,
        )


def reject_calibration_evaluation_overlap(
    calibration_stable_row_ids: frozenset[StableRowId],
    evaluation_stable_row_ids: frozenset[StableRowId],
) -> None:
    if not calibration_stable_row_ids.isdisjoint(evaluation_stable_row_ids):
        raise LeakageError(
            "calibration and evaluation partitions must not share source rows",
            subject=ContractSubject.CALIBRATION,
        )


def reject_score_coordinate_mismatch(records: tuple[ScoreRecord, ...]) -> None:
    if not records:
        return

    iterator = iter(records)
    first_coord = next(iterator).coordinate

    if any(record.coordinate != first_coord for record in iterator):
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

    frame = pl.read_parquet(
        record.path,
        columns=[
            ScoreFrameColumn.OUTCOME_LABEL.value,
            ScoreFrameColumn.STABLE_ROW_ID.value,
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
        ],
    )

    id_col = frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value)

    if id_col.n_unique() != len(id_col):
        raise ScientificContractError(
            "calibration score rows must have unique stable source-row identities",
            subject=ContractSubject.CALIBRATION,
        )

    label_col = frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value)
    score_col = frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value)

    reject_non_benign_labels(
        tuple(label_col.cast(pl.String).to_list()),
        message="attack-labelled rows cannot enter benign calibration construction",
        subject=ContractSubject.CALIBRATION,
        benign_label=benign_label.value,
    )

    row_ids = id_col.cast(pl.String).to_list()
    scores = score_col.cast(pl.Float64).to_list()

    return tuple(
        CalibrationSampleReference(
            client=record.scored_client,
            stable_row_id=StableRowId(row_id),
            score=ScoreValue(score),
        )
        for row_id, score in zip(row_ids, scores, strict=True)
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


def require_common_eligible_cohort(
    cohorts: tuple[EligibleCohort, ...],
) -> EligibleCohort:
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
