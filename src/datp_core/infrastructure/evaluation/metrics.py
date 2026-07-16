from dataclasses import dataclass
from math import fsum, isfinite, sqrt
from typing import NoReturn, Protocol, assert_never

from datp_core.domain.errors import EvaluationError
from datp_core.domain.evaluation.metrics import (
    ClusterMetric,
    DetectionQualityMetric,
    DiagnosticRatio,
    DistributionMetric,
    EquityMetric,
    EstimationMetric,
    OperatingPointMetric,
    ResourceMetric,
)
from datp_core.domain.mathematics.quantiles import nearest_rank_value


@dataclass(frozen=True, slots=True, kw_only=True)
class ComputedMetric[MetricType]:
    metric: MetricType
    value: float


class _MetricWithValue(Protocol):
    @property
    def value(self) -> str: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class OperatingPointMetricRequest:
    metric: OperatingPointMetric
    values: tuple[float, ...]
    target: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class DetectionQualityMetricRequest:
    metric: DetectionQualityMetric
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EquityMetricRequest:
    metric: EquityMetric
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EstimationMetricRequest:
    metric: EstimationMetric
    values: tuple[float, ...]
    reference: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterMetricRequest:
    metric: ClusterMetric
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class DistributionMetricRequest:
    metric: DistributionMetric
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class DiagnosticMetricRequest:
    metric: DiagnosticRatio
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceMetricRequest:
    metric: ResourceMetric
    values: tuple[float, ...]


class MetricCalculator:
    def compute_operating_point(self, request: OperatingPointMetricRequest) -> ComputedMetric[OperatingPointMetric]:
        _require_finite_values(values=request.values, metric=request.metric.value)
        mean = _mean(request.values)
        match request.metric:
            case OperatingPointMetric.FPR | OperatingPointMetric.TPR | OperatingPointMetric.ALERT_BURDEN:
                value = mean
            case OperatingPointMetric.CV_FPR | OperatingPointMetric.CV_TPR:
                value = _coefficient_of_variation(request.values)
            case OperatingPointMetric.IQR_FPR:
                value = _interquartile_range(request.values)
            case OperatingPointMetric.FPR_RANGE:
                value = max(request.values) - min(request.values)
            case OperatingPointMetric.WORST_CLIENT_FPR:
                value = max(request.values)
            case OperatingPointMetric.FPR_TARGET_ATTAINMENT:
                target = _require_target(target=request.target, metric=request.metric.value)
                value = 1 - abs(mean - target)
            case _ as unreachable:
                assert_never(unreachable)
        return ComputedMetric(metric=request.metric, value=value)

    def compute_detection_quality(
        self, request: DetectionQualityMetricRequest
    ) -> ComputedMetric[DetectionQualityMetric]:
        _require_unit_interval(values=request.values, metric=request.metric.value)
        match request.metric:
            case DetectionQualityMetric.P10_MACRO_F1:
                value = nearest_rank_value(values=request.values, percentile=0.1)
            case DetectionQualityMetric.WORST_CLIENT_BA:
                value = min(request.values)
            case (
                DetectionQualityMetric.AUROC
                | DetectionQualityMetric.MACRO_F1
                | DetectionQualityMetric.BALANCED_ACCURACY
            ):
                value = _mean(request.values)
            case _ as unreachable:
                assert_never(unreachable)
        return ComputedMetric(metric=request.metric, value=value)

    def compute_equity(self, request: EquityMetricRequest) -> ComputedMetric[EquityMetric]:
        _require_non_negative(values=request.values, metric=request.metric.value)
        match request.metric:
            case EquityMetric.JAIN_INDEX:
                value = _jain_index(request.values)
            case EquityMetric.GINI_COEFFICIENT:
                value = _gini_coefficient(request.values)
            case EquityMetric.WITHIN_CLUSTER_DISPERSION | EquityMetric.ACROSS_CLUSTER_DISPERSION:
                value = _population_standard_deviation(request.values)
            case _ as unreachable:
                assert_never(unreachable)
        return ComputedMetric(metric=request.metric, value=value)

    def compute_estimation(self, request: EstimationMetricRequest) -> ComputedMetric[EstimationMetric]:
        _require_finite_values(values=request.values, metric=request.metric.value)
        match request.metric:
            case EstimationMetric.QUANTILE_ESTIMATION_ERROR:
                reference = _require_reference(reference=request.reference, metric=request.metric.value)
                value = _mean(tuple(abs(item - reference) for item in request.values))
            case EstimationMetric.THRESHOLD_VARIANCE:
                value = _population_variance(request.values)
            case EstimationMetric.CALIBRATION_SAMPLE_EFFICIENCY:
                _require_non_negative(values=request.values, metric=request.metric.value)
                value = _mean(request.values)
            case EstimationMetric.ELIGIBILITY_COVERAGE | EstimationMetric.CONFORMAL_COVERAGE:
                _require_unit_interval(values=request.values, metric=request.metric.value)
                value = _mean(request.values)
            case _ as unreachable:
                assert_never(unreachable)
        return ComputedMetric(metric=request.metric, value=value)

    def compute_cluster(self, request: ClusterMetricRequest) -> ComputedMetric[ClusterMetric]:
        _require_finite_values(values=request.values, metric=request.metric.value)
        match request.metric:
            case ClusterMetric.ADJUSTED_RAND_INDEX:
                if any(not -1 <= value <= 1 for value in request.values):
                    _raise_invalid(metric=request.metric.value, reason="adjusted Rand values must be in [-1, 1]")
                value = _mean(request.values)
            case ClusterMetric.SILHOUETTE:
                if any(not -1 <= value <= 1 for value in request.values):
                    _raise_invalid(metric=request.metric.value, reason="silhouette values must be in [-1, 1]")
                value = _mean(request.values)
            case _ as unreachable:
                assert_never(unreachable)
        return ComputedMetric(metric=request.metric, value=value)

    def compute_distribution(self, request: DistributionMetricRequest) -> ComputedMetric[DistributionMetric]:
        return _computed_non_negative_mean(metric=request.metric, values=request.values)

    def compute_diagnostic(self, request: DiagnosticMetricRequest) -> ComputedMetric[DiagnosticRatio]:
        return _computed_non_negative_mean(metric=request.metric, values=request.values)

    def compute_resource(self, request: ResourceMetricRequest) -> ComputedMetric[ResourceMetric]:
        _require_non_negative(values=request.values, metric=request.metric.value)
        return ComputedMetric(metric=request.metric, value=fsum(request.values))


def _require_finite_values(*, values: tuple[float, ...], metric: str) -> None:
    if not values or any(not isfinite(value) for value in values):
        _raise_invalid(metric=metric, reason="non-empty finite values required")


def _require_non_negative(*, values: tuple[float, ...], metric: str) -> None:
    _require_finite_values(values=values, metric=metric)
    if any(value < 0 for value in values):
        _raise_invalid(metric=metric, reason="non-negative values required")


def _computed_non_negative_mean[MetricType: _MetricWithValue](
    *, metric: MetricType, values: tuple[float, ...]
) -> ComputedMetric[MetricType]:
    _require_non_negative(values=values, metric=metric.value)
    return ComputedMetric(metric=metric, value=_mean(values))


def _require_unit_interval(*, values: tuple[float, ...], metric: str) -> None:
    _require_finite_values(values=values, metric=metric)
    if any(not 0 <= value <= 1 for value in values):
        _raise_invalid(metric=metric, reason="values must be in [0, 1]")


def _require_target(*, target: float | None, metric: str) -> float:
    if target is None:
        _raise_invalid(metric=metric, reason="a finite target in [0, 1] is required")
    _require_unit_value(value=target, metric=metric, name="target")
    return target


def _require_reference(*, reference: float | None, metric: str) -> float:
    if reference is None or not isfinite(reference):
        _raise_invalid(metric=metric, reason="a finite reference is required")
    return reference


def _require_unit_value(*, value: float, metric: str, name: str) -> None:
    if not isfinite(value):
        _raise_invalid(metric=metric, reason=f"a finite {name} in [0, 1] is required")
    if value < 0 or value > 1:
        _raise_invalid(metric=metric, reason=f"a finite {name} in [0, 1] is required")


def _mean(values: tuple[float, ...]) -> float:
    return fsum(values) / len(values)


def _population_variance(values: tuple[float, ...]) -> float:
    mean = _mean(values)
    return fsum((value - mean) ** 2 for value in values) / len(values)


def _population_standard_deviation(values: tuple[float, ...]) -> float:
    return sqrt(_population_variance(values))


def _coefficient_of_variation(values: tuple[float, ...]) -> float:
    mean = _mean(values)
    if mean == 0:
        _raise_invalid(metric="coefficient_of_variation", reason="undefined for a zero mean")
    return _population_standard_deviation(values) / mean


def _interquartile_range(values: tuple[float, ...]) -> float:
    ordered = tuple(sorted(values))
    middle = len(ordered) // 2
    if middle == 0:
        return 0.0
    return _mean(ordered[-middle:]) - _mean(ordered[:middle])


def _jain_index(values: tuple[float, ...]) -> float:
    denominator = len(values) * fsum(value * value for value in values)
    if denominator == 0:
        _raise_invalid(metric="jain_index", reason="undefined for all-zero values")
    return fsum(values) ** 2 / denominator


def _gini_coefficient(values: tuple[float, ...]) -> float:
    mean = _mean(values)
    if mean == 0:
        _raise_invalid(metric="gini_coefficient", reason="undefined for a zero mean")
    absolute_differences = fsum(abs(first - second) for first in values for second in values)
    return absolute_differences / (2 * len(values) ** 2 * mean)


def _raise_invalid(*, metric: str, reason: str) -> NoReturn:
    raise EvaluationError(
        detail="metric calculation requires valid family-specific inputs",
        metric=metric,
        scope=reason,
    )
