from enum import StrEnum

import numpy as np
from pydantic import model_validator
from scipy.spatial.distance import jensenshannon

from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import MetricValue, ScoreValue, ThresholdValue
from datp_core.data.populations.contracts import ClientIdentity

_DENOMINATOR_MINIMUM = 1e-12
_FEDAVG_GRID_QUANTILE_COUNT = 64


class ModelAlignmentMetric(StrEnum):
    MODEL_ALIGNMENT_HETEROGENEITY = "model_alignment_heterogeneity"
    LOCATION_DISPERSION = "location_dispersion"
    SCALE_DISPERSION = "scale_dispersion"
    LOCAL_THRESHOLD_DISPERSION = "local_threshold_dispersion"
    NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE = "normalized_shared_local_threshold_distance"


class ModelAlignmentUnavailableReason(StrEnum):
    NONPOSITIVE_SCALE = "unavailable_nonpositive_scale"
    DEGENERATE_FEDAVG_JSD_GRID = "unavailable_degenerate_fedavg_jsd_grid"
    INSUFFICIENT_CLIENTS = "unavailable_insufficient_clients"


class AlignmentReductionUnavailableReason(StrEnum):
    NO_POSITIVE_FEDAVG_REFERENCE = "unavailable_no_positive_fedavg_reference"
    CONDITION_METRIC_UNAVAILABLE = "unavailable_condition_metric"


class ModelAlignmentMetricOutcome(StrictModel):
    metric: ModelAlignmentMetric
    value: MetricValue | None
    unavailable_reason: ModelAlignmentUnavailableReason | None

    @model_validator(mode="after")
    def validate_availability(self) -> "ModelAlignmentMetricOutcome":
        if (self.value is None) == (self.unavailable_reason is None):
            raise ValueError("alignment metric must have exactly one value or unavailable reason")
        return self


class ModelAlignmentClientScores(StrictModel):
    client: ClientIdentity
    calibration_scores: tuple[ScoreValue, ...]

    @model_validator(mode="after")
    def validate_scores(self) -> "ModelAlignmentClientScores":
        if not self.calibration_scores:
            raise ValueError("alignment requires at least one calibration score per client")
        if any(not np.isfinite(value.value) for value in self.calibration_scores):
            raise ValueError("alignment calibration scores must be finite")
        return self


class ModelAlignmentCondition(StrictModel):
    client_scores: tuple[ModelAlignmentClientScores, ...]
    shared_threshold: ThresholdValue

    @model_validator(mode="after")
    def validate_clients(self) -> "ModelAlignmentCondition":
        clients = tuple(item.client for item in self.client_scores)
        if len(clients) < 2:
            raise ValueError("alignment requires at least two clients")
        if len(clients) != len(frozenset(clients)):
            raise ValueError("alignment clients must be unique")
        return self


class FedAvgAlignmentGrid(StrictModel):
    interior_edges: tuple[ScoreValue, ...]

    @property
    def available(self) -> bool:
        return bool(self.interior_edges)


class ModelAlignmentResult(StrictModel):
    grid: FedAvgAlignmentGrid
    metrics: tuple[ModelAlignmentMetricOutcome, ...]

    @model_validator(mode="after")
    def validate_metrics(self) -> "ModelAlignmentResult":
        if tuple(item.metric for item in self.metrics) != tuple(ModelAlignmentMetric):
            raise ValueError("alignment results must report every metric in canonical order")
        return self


class AlignmentReductionOutcome(StrictModel):
    metric: ModelAlignmentMetric
    value: MetricValue | None
    unavailable_reason: AlignmentReductionUnavailableReason | None

    @model_validator(mode="after")
    def validate_availability(self) -> "AlignmentReductionOutcome":
        if (self.value is None) == (self.unavailable_reason is None):
            raise ValueError("alignment reduction must have exactly one value or unavailable reason")
        return self


def fedavg_alignment_grid(condition: ModelAlignmentCondition) -> FedAvgAlignmentGrid:
    return fedavg_alignment_grid_for_scores(condition.client_scores)


def fedavg_alignment_grid_for_scores(
    client_scores: tuple[ModelAlignmentClientScores, ...],
) -> FedAvgAlignmentGrid:
    pooled = np.concatenate(tuple(_scores(item) for item in client_scores))
    quantiles = np.quantile(
        pooled,
        np.arange(1, _FEDAVG_GRID_QUANTILE_COUNT, dtype=np.float64) / _FEDAVG_GRID_QUANTILE_COUNT,
        method="linear",
    )
    finite = quantiles[np.isfinite(quantiles)]
    unique = np.unique(finite)
    return FedAvgAlignmentGrid(interior_edges=tuple(ScoreValue(float(value)) for value in unique))


def model_alignment(
    condition: ModelAlignmentCondition,
    *,
    grid: FedAvgAlignmentGrid,
) -> ModelAlignmentResult:
    ordered = tuple(sorted(condition.client_scores, key=lambda item: item.client))
    medians = np.asarray([np.quantile(_scores(item), 0.5, method="linear") for item in ordered], dtype=np.float64)
    interquartile_ranges = np.asarray(
        [
            np.quantile(_scores(item), 0.75, method="linear")
            - np.quantile(_scores(item), 0.25, method="linear")
            for item in ordered
        ],
        dtype=np.float64,
    )
    local_thresholds = np.asarray(
        [np.quantile(_scores(item), 0.95, method="linear") for item in ordered], dtype=np.float64
    )
    mean_distance = float(np.mean(np.abs(condition.shared_threshold.value - local_thresholds)))
    outcomes = (
        _heterogeneity_outcome(ordered, grid),
        _dispersion_outcome(ModelAlignmentMetric.LOCATION_DISPERSION, medians),
        _dispersion_outcome(ModelAlignmentMetric.SCALE_DISPERSION, interquartile_ranges),
        _dispersion_outcome(ModelAlignmentMetric.LOCAL_THRESHOLD_DISPERSION, local_thresholds),
        _normalized_distance_outcome(mean_distance, local_thresholds),
    )
    return ModelAlignmentResult(grid=grid, metrics=outcomes)


def alignment_reductions(
    reference: ModelAlignmentResult,
    condition: ModelAlignmentResult,
) -> tuple[AlignmentReductionOutcome, ...]:
    reference_by_metric = {outcome.metric: outcome for outcome in reference.metrics}
    condition_by_metric = {outcome.metric: outcome for outcome in condition.metrics}
    return tuple(
        _alignment_reduction(
            metric,
            reference_by_metric[metric],
            condition_by_metric[metric],
        )
        for metric in ModelAlignmentMetric
    )


def _alignment_reduction(
    metric: ModelAlignmentMetric,
    reference: ModelAlignmentMetricOutcome,
    condition: ModelAlignmentMetricOutcome,
) -> AlignmentReductionOutcome:
    if reference.value is None or reference.value.value <= _DENOMINATOR_MINIMUM:
        return AlignmentReductionOutcome(
            metric=metric,
            value=None,
            unavailable_reason=AlignmentReductionUnavailableReason.NO_POSITIVE_FEDAVG_REFERENCE,
        )
    if condition.value is None:
        return AlignmentReductionOutcome(
            metric=metric,
            value=None,
            unavailable_reason=AlignmentReductionUnavailableReason.CONDITION_METRIC_UNAVAILABLE,
        )
    return AlignmentReductionOutcome(
        metric=metric,
        value=MetricValue(1.0 - condition.value.value / reference.value.value),
        unavailable_reason=None,
    )


def _heterogeneity_outcome(
    observations: tuple[ModelAlignmentClientScores, ...],
    grid: FedAvgAlignmentGrid,
) -> ModelAlignmentMetricOutcome:
    if not grid.available:
        return ModelAlignmentMetricOutcome(
            metric=ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY,
            value=None,
            unavailable_reason=ModelAlignmentUnavailableReason.DEGENERATE_FEDAVG_JSD_GRID,
        )
    edges = np.asarray([edge.value for edge in grid.interior_edges], dtype=np.float64)
    histograms = tuple(_fixed_grid_histogram(_scores(item), edges) for item in observations)
    distances = tuple(
        float(jensenshannon(left, right, base=2.0) ** 2)
        for index, left in enumerate(histograms)
        for right in histograms[index + 1 :]
    )
    return ModelAlignmentMetricOutcome(
        metric=ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY,
        value=MetricValue(float(np.mean(distances))),
        unavailable_reason=None,
    )


def _dispersion_outcome(metric: ModelAlignmentMetric, values: np.ndarray) -> ModelAlignmentMetricOutcome:
    mean = float(np.mean(values))
    if not np.isfinite(mean) or mean <= _DENOMINATOR_MINIMUM:
        return ModelAlignmentMetricOutcome(
            metric=metric,
            value=None,
            unavailable_reason=ModelAlignmentUnavailableReason.NONPOSITIVE_SCALE,
        )
    return ModelAlignmentMetricOutcome(
        metric=metric,
        value=MetricValue(float(np.std(values, ddof=1) / mean)),
        unavailable_reason=None,
    )


def _normalized_distance_outcome(mean_distance: float, local_thresholds: np.ndarray) -> ModelAlignmentMetricOutcome:
    mean_local_threshold = float(np.mean(local_thresholds))
    if not np.isfinite(mean_local_threshold) or mean_local_threshold <= _DENOMINATOR_MINIMUM:
        return ModelAlignmentMetricOutcome(
            metric=ModelAlignmentMetric.NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE,
            value=None,
            unavailable_reason=ModelAlignmentUnavailableReason.NONPOSITIVE_SCALE,
        )
    return ModelAlignmentMetricOutcome(
        metric=ModelAlignmentMetric.NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE,
        value=MetricValue(mean_distance / mean_local_threshold),
        unavailable_reason=None,
    )


def _scores(observation: ModelAlignmentClientScores) -> np.ndarray:
    return np.asarray([value.value for value in observation.calibration_scores], dtype=np.float64)


def _fixed_grid_histogram(scores: np.ndarray, edges: np.ndarray) -> np.ndarray:
    bins = np.concatenate((np.asarray([-np.inf]), edges, np.asarray([np.inf])))
    counts, _ = np.histogram(scores, bins=bins)
    return counts.astype(np.float64) / counts.sum()
