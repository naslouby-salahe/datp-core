"""Held-out benign coverage diagnostics for persisted conformal thresholds."""

from dataclasses import dataclass
from math import isfinite

import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.domain.enums import MetricId, ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import checksum_file
from datp_core.domain.values.counts import ConformalRankIndex, RowCount, Seed
from datp_core.domain.values.ratios import CoverageTarget, Quantile, ThresholdValue
from datp_core.evaluation.metric_semantics import (
    available,
    metric_value,
    unavailable,
)
from datp_core.evaluation.models import (
    HeldOutBenignScore,
    MetricAvailability,
    MetricReason,
    MetricStatus,
    metric_by_id,
    validate_metric_set,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.inference import ScoreRecord
from datp_core.thresholding.methods.conformal import ConformalAssignment

_COVERAGE_METRICS = frozenset(
    {
        MetricId.TARGET_COVERAGE,
        MetricId.ACHIEVED_COVERAGE,
        MetricId.SIGNED_COVERAGE_ERROR,
        MetricId.ABSOLUTE_COVERAGE_ERROR,
    }
)


@dataclass(frozen=True, slots=True)
class ConformalCoverageDiagnostic:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    target_coverage: CoverageTarget
    calibration_count: RowCount
    finite_sample_rank_index: ConformalRankIndex
    effective_quantile: Quantile
    tie_count: RowCount
    threshold: ThresholdValue
    metrics: tuple[MetricAvailability, ...]

    def __post_init__(self) -> None:
        if self.calibration_count.value < 1:
            raise ScientificContractError("conformal diagnostics require a positive calibration count")
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("conformal coverage coordinate must match the client and training seed")
        if not isfinite(self.effective_quantile.value) or not 0 < self.effective_quantile.value <= 1:
            raise ScientificContractError("conformal effective quantile must be finite and in (0, 1]")
        if not isfinite(self.threshold.value):
            raise ScientificContractError("conformal threshold provenance must be finite")
        validate_metric_set(self.metrics, _COVERAGE_METRICS)
        target = metric_by_id(self.metrics, MetricId.TARGET_COVERAGE)
        if target.value is None or target.value.value != self.target_coverage.value:
            raise ScientificContractError("coverage target metric must match the declared target")
        outcomes = tuple(
            metric_by_id(self.metrics, metric)
            for metric in (
                MetricId.ACHIEVED_COVERAGE,
                MetricId.SIGNED_COVERAGE_ERROR,
                MetricId.ABSOLUTE_COVERAGE_ERROR,
            )
        )
        if len({item.status for item in outcomes}) != 1:
            raise ScientificContractError("coverage outcome metrics must share one availability state")

    @property
    def achieved_held_out_benign_coverage(self) -> float | None:
        return metric_value(metric_by_id(self.metrics, MetricId.ACHIEVED_COVERAGE))

    @property
    def signed_coverage_error(self) -> float | None:
        return metric_value(metric_by_id(self.metrics, MetricId.SIGNED_COVERAGE_ERROR))

    @property
    def absolute_coverage_error(self) -> float | None:
        return metric_value(metric_by_id(self.metrics, MetricId.ABSOLUTE_COVERAGE_ERROR))

    @property
    def unavailable_reason(self) -> MetricReason | None:
        return metric_by_id(
            self.metrics,
            MetricId.ACHIEVED_COVERAGE,
        ).reason


def evaluate_held_out_conformal_coverage(
    assignment: ConformalAssignment,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    target_coverage: CoverageTarget,
    held_out_benign_scores: tuple[HeldOutBenignScore, ...],
) -> ConformalCoverageDiagnostic:
    _validate_scores(assignment.client, coordinate, held_out_benign_scores)
    if coordinate.population is not assignment.client.population or coordinate.training_seed != training_seed:
        raise ScientificContractError(
            "conformal coverage coordinate must match the assignment client and training seed"
        )
    metrics = _coverage_metrics(
        assignment,
        target_coverage,
        held_out_benign_scores,
    )
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
        metrics=metrics,
    )


def _coverage_metrics(
    assignment: ConformalAssignment,
    target_coverage: CoverageTarget,
    scores: tuple[HeldOutBenignScore, ...],
) -> tuple[MetricAvailability, ...]:
    if not scores:
        return (
            available(MetricId.TARGET_COVERAGE, target_coverage.value),
            *tuple(
                unavailable(
                    metric,
                    MetricStatus.UNAVAILABLE,
                    MetricReason.EMPTY_BENIGN_DENOMINATOR,
                    denominator=0,
                )
                for metric in (
                    MetricId.ACHIEVED_COVERAGE,
                    MetricId.SIGNED_COVERAGE_ERROR,
                    MetricId.ABSOLUTE_COVERAGE_ERROR,
                )
            ),
        )
    denominator = len(scores)
    achieved = sum(item.score <= assignment.threshold for item in scores) / denominator
    signed_error = achieved - target_coverage.value
    return (
        available(MetricId.TARGET_COVERAGE, target_coverage.value),
        available(
            MetricId.ACHIEVED_COVERAGE,
            achieved,
            denominator=denominator,
        ),
        available(
            MetricId.SIGNED_COVERAGE_ERROR,
            signed_error,
            denominator=denominator,
        ),
        available(
            MetricId.ABSOLUTE_COVERAGE_ERROR,
            abs(signed_error),
            denominator=denominator,
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


def _verify_score_rows(
    scores: tuple[HeldOutBenignScore, ...],
) -> None:
    records: list[ScoreRecord] = []
    for item in scores:
        if item.score_record not in records:
            records.append(item.score_record)
    for record in records:
        supplied_rows = tuple(item for item in scores if item.score_record == record)
        _verify_record_rows(record, supplied_rows)


def _verify_record_rows(
    record: ScoreRecord,
    supplied_rows: tuple[HeldOutBenignScore, ...],
) -> None:
    required = (
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    )
    if not record.path.is_file() or checksum_file(record.path) != record.checksum:
        raise ScientificContractError("held-out coverage score provenance is unavailable or changed")
    frame = pl.read_parquet(record.path)
    if any(column not in frame.columns for column in required) or frame.height != record.row_count.value:
        raise ScientificContractError("held-out coverage score provenance has an invalid schema or row count")
    stable_row_ids = tuple(item.stable_row_id for item in supplied_rows)
    observed_rows = frame.filter(pl.col(ScoreFrameColumn.STABLE_ROW_ID.value).is_in(stable_row_ids)).select(required)
    if observed_rows.height != len(supplied_rows):
        raise ScientificContractError("held-out coverage score rows are not uniquely proven by their score artifact")
    observed = tuple(
        (
            str(row[0]),
            PopulationOutcomeLabel(str(row[1])),
            float(row[2]),
        )
        for row in observed_rows.iter_rows()
    )
    if len({item[0] for item in observed}) != len(supplied_rows):
        raise ScientificContractError("held-out coverage score rows are not uniquely proven by their score artifact")
    for item in supplied_rows:
        matches = tuple(
            (label, score) for stable_row_id, label, score in observed if stable_row_id == item.stable_row_id
        )
        if len(matches) != 1 or matches[0] != (
            item.outcome_label,
            item.score.value,
        ):
            raise ScientificContractError("held-out coverage score row is not proven by its score artifact")
