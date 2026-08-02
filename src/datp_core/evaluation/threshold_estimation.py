"""Threshold-estimation diagnostics against an exact pooled benign reference."""

from dataclasses import dataclass
from enum import StrEnum
from itertools import groupby

import numpy as np
import polars as pl

from datp_core.domain.enums import MetricId, ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    CalibrationSize,
    Quantile,
    ReplicateIndex,
    Seed,
    ThresholdValue,
    checksum_file,
)
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import HeldOutBenignScore, MetricReason, MetricStatus, ThresholdEstimationResult
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.scoring.models import ScoreRecord


class ThresholdEstimationUnavailableReason(StrEnum):
    """Closed undefined states for threshold-estimation quantities."""

    REFERENCE_THRESHOLD_IS_ZERO = "reference_threshold_is_zero"


@dataclass(frozen=True, slots=True)
class ThresholdEstimationProvenance:
    """Immutable coordinate and calibration identity for one threshold estimate."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    calibration_size: CalibrationSize
    replicate_index: ReplicateIndex
    quantile: Quantile

    def __post_init__(self) -> None:
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("threshold-estimation coordinate must match client and training seed")


@dataclass(frozen=True, slots=True)
class ThresholdEstimationDiagnostic:
    """One threshold estimate assessed only with benign score evidence."""

    provenance: ThresholdEstimationProvenance
    estimated_threshold: ThresholdValue
    exact_pooled_benign_quantile_reference: ThresholdValue
    target_exceedance: float
    achieved_benign_exceedance: float
    absolute_threshold_error: float
    relative_threshold_error_status: MetricStatus
    relative_threshold_error: float | None
    signed_attainment_error: float
    absolute_attainment_error: float
    relative_error_unavailable_reason: ThresholdEstimationUnavailableReason | None
    result: ThresholdEstimationResult

    def __post_init__(self) -> None:
        if not 0 < self.target_exceedance < 1 or not 0 <= self.achieved_benign_exceedance <= 1:
            raise ScientificContractError("threshold-estimation exceedance values must be valid probabilities")
        if min(self.absolute_threshold_error, self.absolute_attainment_error) < 0:
            raise ScientificContractError("absolute threshold diagnostics must be non-negative")
        is_available = self.relative_threshold_error_status is MetricStatus.AVAILABLE
        if is_available != (self.relative_threshold_error is not None):
            raise ScientificContractError("relative threshold-error availability must match its value")
        if is_available == (self.relative_error_unavailable_reason is not None):
            raise ScientificContractError("relative threshold-error availability must match its reason")


@dataclass(frozen=True, slots=True)
class SampleEfficiencyPoint:
    """Nested-replicate threshold variability at one calibration size within one seed."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    calibration_size: CalibrationSize
    replicate_count: int
    mean_threshold: float
    threshold_variance_across_nested_replicates: float

    def __post_init__(self) -> None:
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("sample-efficiency coordinate must match client and training seed")
        if self.replicate_count < 1 or self.threshold_variance_across_nested_replicates < 0:
            raise ScientificContractError("sample-efficiency points require non-negative population variance")


def evaluate_threshold_estimate(
    *,
    provenance: ThresholdEstimationProvenance,
    estimated_threshold: ThresholdValue,
    exact_pooled_benign_quantile_reference: ThresholdValue,
    held_out_benign_scores: tuple[HeldOutBenignScore, ...],
) -> ThresholdEstimationDiagnostic:
    """Calculate one declared diagnostic without using attack labels or scores."""
    _validate_benign_scores(provenance, held_out_benign_scores)
    target_exceedance = 1.0 - provenance.quantile.value
    achieved = sum(score.score > estimated_threshold for score in held_out_benign_scores) / len(held_out_benign_scores)
    signed_attainment_error = achieved - target_exceedance
    absolute_error = abs(estimated_threshold.value - exact_pooled_benign_quantile_reference.value)
    reference = exact_pooled_benign_quantile_reference.value
    if reference == 0.0:
        relative_status = MetricStatus.UNDEFINED
        relative_error = None
        reason = ThresholdEstimationUnavailableReason.REFERENCE_THRESHOLD_IS_ZERO
    else:
        relative_status = MetricStatus.AVAILABLE
        relative_error = absolute_error / abs(reference)
        reason = None
    return ThresholdEstimationDiagnostic(
        provenance=provenance,
        estimated_threshold=estimated_threshold,
        exact_pooled_benign_quantile_reference=exact_pooled_benign_quantile_reference,
        target_exceedance=target_exceedance,
        achieved_benign_exceedance=achieved,
        absolute_threshold_error=absolute_error,
        relative_threshold_error_status=relative_status,
        relative_threshold_error=relative_error,
        signed_attainment_error=signed_attainment_error,
        absolute_attainment_error=abs(signed_attainment_error),
        relative_error_unavailable_reason=reason,
        result=ThresholdEstimationResult(
            absolute_threshold_error=available(MetricId.ABSOLUTE_THRESHOLD_ERROR, absolute_error),
            relative_threshold_error=(
                unavailable(
                    MetricId.RELATIVE_THRESHOLD_ERROR,
                    MetricStatus.UNDEFINED,
                    MetricReason.ZERO_MEAN,
                )
                if relative_error is None
                else available(MetricId.RELATIVE_THRESHOLD_ERROR, relative_error)
            ),
            signed_attainment_error=available(MetricId.SIGNED_ATTAINMENT_ERROR, signed_attainment_error),
            absolute_attainment_error=available(MetricId.ABSOLUTE_ATTAINMENT_ERROR, abs(signed_attainment_error)),
        ),
    )


def sample_efficiency_curve(
    diagnostics: tuple[ThresholdEstimationDiagnostic, ...],
) -> tuple[SampleEfficiencyPoint, ...]:
    """Summarize nested calibration replicates inside each client/seed/size cell."""
    ordered = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                item.provenance.coordinate.model.value,
                item.provenance.coordinate.preprocessing_identity.value,
                item.provenance.client.client_id,
                item.provenance.training_seed.value,
                item.provenance.calibration_size.value,
            ),
        )
    )
    points: list[SampleEfficiencyPoint] = []
    for key, items in groupby(
        ordered,
        key=lambda item: (
            item.provenance.client,
            item.provenance.coordinate,
            item.provenance.training_seed,
            item.provenance.calibration_size,
        ),
    ):
        replicate_group = tuple(items)
        indexes = tuple(item.provenance.replicate_index.value for item in replicate_group)
        if len(indexes) != len(frozenset(indexes)):
            raise ScientificContractError("nested threshold replicates must be unique within a size cell")
        values = np.asarray(tuple(item.estimated_threshold.value for item in replicate_group), dtype=np.float64)
        points.append(
            SampleEfficiencyPoint(
                client=key[0],
                coordinate=key[1],
                training_seed=key[2],
                calibration_size=key[3],
                replicate_count=len(replicate_group),
                mean_threshold=float(np.mean(values)),
                threshold_variance_across_nested_replicates=float(np.var(values, ddof=0)),
            )
        )
    return tuple(points)


def _validate_benign_scores(
    provenance: ThresholdEstimationProvenance,
    scores: tuple[HeldOutBenignScore, ...],
) -> None:
    if not scores:
        raise ScientificContractError("threshold diagnostics require non-empty finite held-out benign scores")
    stable_row_ids = tuple(item.stable_row_id for item in scores)
    if len(stable_row_ids) != len(frozenset(stable_row_ids)):
        raise ScientificContractError("threshold diagnostics require unique held-out stable row identities")
    if any(item.client != provenance.client for item in scores):
        raise ScientificContractError("threshold diagnostics require scores from the evaluated client")
    if any(item.score_record.coordinate != provenance.coordinate for item in scores):
        raise ScientificContractError(
            "threshold diagnostics require score provenance matching the evaluation coordinate"
        )
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
            raise ScientificContractError("threshold diagnostics score provenance is unavailable or changed")
        frame = pl.read_parquet(record.path)
        if any(column not in frame.columns for column in required) or frame.height != record.row_count.value:
            raise ScientificContractError("threshold diagnostics score provenance has an invalid schema or row count")
        stable_row_ids = [item.stable_row_id for item in supplied_rows]
        observed_rows = frame.filter(pl.col(ScoreFrameColumn.STABLE_ROW_ID.value).is_in(stable_row_ids))
        if observed_rows.height != len(supplied_rows):
            raise ScientificContractError(
                "threshold diagnostics score rows are not uniquely proven by their score artifact"
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
                "threshold diagnostics score rows are not uniquely proven by their score artifact"
            )
        for item in supplied_rows:
            provenance = observed.get(item.stable_row_id)
            if provenance != (item.outcome_label, item.score.value):
                raise ScientificContractError("threshold diagnostics score row is not proven by its score artifact")
