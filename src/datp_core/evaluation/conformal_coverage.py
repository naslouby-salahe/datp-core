"""Held-out benign coverage diagnostics for persisted conformal thresholds."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import polars as pl

from datp_core.domain.enums import MetricId, ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CoverageTarget, Quantile, RowCount, Seed, ThresholdValue, checksum_file
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import CoverageResult, HeldOutBenignScore, MetricReason, MetricStatus
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.scoring.models import ScoreRecord
from datp_core.thresholding.models import ConformalAssignment


class CoverageUnavailableReason(StrEnum):
    """Closed reasons held-out conformal coverage cannot be calculated."""

    NO_HELD_OUT_BENIGN_SCORES = "no_held_out_benign_scores"


@dataclass(frozen=True, slots=True)
class ConformalCoverageDiagnostic:
    """Coverage evidence for one client and one training seed."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    target_coverage: CoverageTarget
    calibration_count: RowCount
    finite_sample_rank_index: int
    effective_quantile: Quantile
    tie_count: RowCount
    threshold: ThresholdValue
    achieved_held_out_benign_coverage: float | None
    signed_coverage_error: float | None
    absolute_coverage_error: float | None
    unavailable_reason: CoverageUnavailableReason | None
    result: CoverageResult

    def __post_init__(self) -> None:
        is_available = self.result.achieved_held_out_benign_coverage.status is MetricStatus.AVAILABLE
        values = (
            self.achieved_held_out_benign_coverage,
            self.signed_coverage_error,
            self.absolute_coverage_error,
        )
        if self.calibration_count.value < 1 or self.finite_sample_rank_index < 1:
            raise ScientificContractError("conformal diagnostics require a positive calibration count and rank")
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("conformal coverage coordinate must match the client and training seed")
        if not isfinite(self.effective_quantile.value) or not 0 < self.effective_quantile.value <= 1:
            raise ScientificContractError("conformal effective quantile must be finite and in (0, 1]")
        if self.tie_count.value < 0 or not isfinite(self.threshold.value):
            raise ScientificContractError("conformal threshold provenance must be finite")
        if is_available:
            if any(value is None for value in values) or self.unavailable_reason is not None:
                raise ScientificContractError("available coverage requires all values and no unavailable reason")
        elif any(value is not None for value in values) or self.unavailable_reason is None:
            raise ScientificContractError("unavailable coverage requires a reason and no metric values")


def evaluate_held_out_conformal_coverage(
    assignment: ConformalAssignment,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    target_coverage: CoverageTarget,
    held_out_benign_scores: tuple[HeldOutBenignScore, ...],
) -> ConformalCoverageDiagnostic:
    """Evaluate a persisted conformal threshold on held-out benign rows only."""
    _validate_scores(assignment.client, coordinate, held_out_benign_scores)
    if coordinate.population is not assignment.client.population or coordinate.training_seed != training_seed:
        raise ScientificContractError(
            "conformal coverage coordinate must match the assignment client and training seed"
        )
    if not held_out_benign_scores:
        return ConformalCoverageDiagnostic(
            client=assignment.client,
            coordinate=coordinate,
            training_seed=training_seed,
            target_coverage=target_coverage,
            calibration_count=assignment.calibration_count,
            finite_sample_rank_index=assignment.rank_index,
            effective_quantile=assignment.effective_quantile,
            tie_count=assignment.tie_count,
            threshold=assignment.threshold,
            achieved_held_out_benign_coverage=None,
            signed_coverage_error=None,
            absolute_coverage_error=None,
            unavailable_reason=CoverageUnavailableReason.NO_HELD_OUT_BENIGN_SCORES,
            result=CoverageResult(
                target_coverage=available(MetricId.TARGET_COVERAGE, target_coverage.value),
                achieved_held_out_benign_coverage=unavailable(
                    MetricId.ACHIEVED_COVERAGE,
                    MetricStatus.UNAVAILABLE,
                    MetricReason.EMPTY_BENIGN_DENOMINATOR,
                    denominator=0,
                ),
                signed_coverage_error=unavailable(
                    MetricId.SIGNED_COVERAGE_ERROR,
                    MetricStatus.UNAVAILABLE,
                    MetricReason.EMPTY_BENIGN_DENOMINATOR,
                    denominator=0,
                ),
                absolute_coverage_error=unavailable(
                    MetricId.ABSOLUTE_COVERAGE_ERROR,
                    MetricStatus.UNAVAILABLE,
                    MetricReason.EMPTY_BENIGN_DENOMINATOR,
                    denominator=0,
                ),
            ),
        )
    achieved = sum(score.score <= assignment.threshold for score in held_out_benign_scores) / len(
        held_out_benign_scores
    )
    signed_error = achieved - target_coverage.value
    return ConformalCoverageDiagnostic(
        client=assignment.client,
        coordinate=coordinate,
        training_seed=training_seed,
        target_coverage=target_coverage,
        calibration_count=assignment.calibration_count,
        finite_sample_rank_index=assignment.rank_index,
        effective_quantile=assignment.effective_quantile,
        tie_count=assignment.tie_count,
        threshold=assignment.threshold,
        achieved_held_out_benign_coverage=achieved,
        signed_coverage_error=signed_error,
        absolute_coverage_error=abs(signed_error),
        unavailable_reason=None,
        result=CoverageResult(
            target_coverage=available(MetricId.TARGET_COVERAGE, target_coverage.value),
            achieved_held_out_benign_coverage=available(
                MetricId.ACHIEVED_COVERAGE, achieved, denominator=len(held_out_benign_scores)
            ),
            signed_coverage_error=available(
                MetricId.SIGNED_COVERAGE_ERROR, signed_error, denominator=len(held_out_benign_scores)
            ),
            absolute_coverage_error=available(
                MetricId.ABSOLUTE_COVERAGE_ERROR,
                abs(signed_error),
                denominator=len(held_out_benign_scores),
            ),
        ),
    )


def _validate_scores(
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    scores: tuple[HeldOutBenignScore, ...],
) -> None:
    stable_row_ids = tuple(item.stable_row_id for item in scores)
    if len(stable_row_ids) != len(frozenset(stable_row_ids)):
        raise ScientificContractError("held-out coverage rows must be unique")
    if any(item.client != client for item in scores):
        raise ScientificContractError("held-out coverage scores must belong to the threshold-assigned client")
    if any(item.score_record.coordinate != coordinate for item in scores):
        raise ScientificContractError("held-out coverage score provenance must match the evaluation coordinate")
    _verify_score_rows(scores)


def _verify_score_rows(scores: tuple[HeldOutBenignScore, ...]) -> None:
    """Reject rows not demonstrably present in an unchanged held-out score artifact."""
    by_record: dict[ScoreRecord, list[HeldOutBenignScore]] = {}
    for item in scores:
        by_record.setdefault(item.score_record, []).append(item)
    required = (
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    )
    for record, supplied_rows in by_record.items():
        if not record.path.is_file() or checksum_file(record.path) != record.checksum:
            raise ScientificContractError("held-out coverage score provenance is unavailable or changed")
        frame = pl.read_parquet(record.path)
        if any(column not in frame.columns for column in required) or frame.height != record.row_count.value:
            raise ScientificContractError("held-out coverage score provenance has an invalid schema or row count")
        stable_row_ids = [item.stable_row_id for item in supplied_rows]
        observed_rows = frame.filter(pl.col(ScoreFrameColumn.STABLE_ROW_ID.value).is_in(stable_row_ids))
        if observed_rows.height != len(supplied_rows):
            raise ScientificContractError(
                "held-out coverage score rows are not uniquely proven by their score artifact"
            )
        observed = {
            str(row[ScoreFrameColumn.STABLE_ROW_ID.value]): (
                PopulationOutcomeLabel(str(row[ScoreFrameColumn.OUTCOME_LABEL.value])),
                float(row[ScoreFrameColumn.RECONSTRUCTION_ERROR.value]),
            )
            for row in observed_rows.select(required).iter_rows(named=True)
        }
        if len(observed) != len(supplied_rows):
            raise ScientificContractError(
                "held-out coverage score rows are not uniquely proven by their score artifact"
            )
        for item in supplied_rows:
            provenance = observed.get(item.stable_row_id)
            if provenance != (item.outcome_label, item.score.value):
                raise ScientificContractError("held-out coverage score row is not proven by its score artifact")
