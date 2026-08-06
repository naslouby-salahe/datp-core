"""Cross-client aggregates over the declared, never row-weighted cohort."""

import numpy as np

from datp_core.domain.enums import EvaluationCohort, MetricId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.ratios import Quantile
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import (
    FPR_POPULATION_METRIC_IDS,
    ClientMetricResult,
    MetricAvailability,
    MetricReason,
    MetricStatus,
    MetricWarning,
    PopulationMetricResult,
    WarningCode,
)
from datp_core.protocols.metrics import NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF


def calculate_population_metrics(
    results: tuple[ClientMetricResult, ...],
    *,
    cohort: EvaluationCohortManifest | None = None,
) -> PopulationMetricResult:
    """Aggregate one threshold method's client results without pooling rows for FPR dispersion."""
    if not results:
        raise ScientificContractError("population evaluation requires client results")
    first = results[0]
    if len({result.client for result in results}) != len(results):
        raise ScientificContractError("population results must have one record per client")
    if any(
        result.coordinate != first.coordinate
        or result.threshold_method is not first.threshold_method
        or result.evidence_role is not first.evidence_role
        for result in results
    ):
        raise ScientificContractError(
            "population results require one fixed coordinate, threshold method, and evidence role"
        )
    fpr_evaluable = tuple(result for result in results if result.cohort is EvaluationCohort.FPR_EVALUABLE)
    fallback = tuple(result for result in results if result.cohort is EvaluationCohort.DEPLOYMENT_FALLBACK)
    unavailable_records = tuple(result for result in results if result.cohort is EvaluationCohort.UNAVAILABLE)
    fpr_records = tuple(_metric(result, MetricId.FALSE_POSITIVE_RATE) for result in fpr_evaluable)
    fpr_values = tuple(item.value.value for item in fpr_records if item.value is not None)
    attack_evaluable = tuple(result for result in fpr_evaluable if result.attack_evaluable)
    if cohort is None:
        calibration_eligible_count = len(fpr_evaluable)
    else:
        calibration_eligible_count = sum(1 for record in cohort.records if record.calibration_eligible)
    metric_records, warnings = _population_metric_records(fpr_evaluable, fpr_values)
    return PopulationMetricResult(
        coordinate=first.coordinate,
        threshold_method=first.threshold_method,
        cohort=EvaluationCohort.FPR_EVALUABLE,
        metrics=metric_records,
        candidate_client_count=_count(len(results)),
        calibration_eligible_client_count=_count(calibration_eligible_count),
        fpr_evaluable_client_count=_count(len(fpr_values)),
        attack_evaluable_client_count=_count(len(attack_evaluable)),
        deployment_fallback_count=_count(len(fallback)),
        unavailable_client_count=_count(len(unavailable_records)),
        excluded_clients=tuple(
            sorted(
                (result.client for result in results if result not in fpr_evaluable),
                key=lambda item: item.client_id,
            )
        ),
        warnings=warnings,
        evidence_role=first.evidence_role,
    )


def _population_metric_records(
    results: tuple[ClientMetricResult, ...], fpr_values: tuple[float, ...]
) -> tuple[tuple[MetricAvailability, ...], tuple[MetricWarning, ...]]:
    fpr_metrics, warnings = _fpr_aggregates(fpr_values)
    return (
        (*fpr_metrics, *_attack_aggregates(results)),
        warnings,
    )


def _fpr_aggregates(values: tuple[float, ...]) -> tuple[tuple[MetricAvailability, ...], tuple[MetricWarning, ...]]:
    if not values:
        absent = tuple(
            unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
            for metric in FPR_POPULATION_METRIC_IDS
        )
        return absent, ()
    array = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(array))
    std = float(np.std(array, ddof=0))
    metrics: list[MetricAvailability] = [
        available(MetricId.MEAN_FPR, mean, denominator=len(values)),
        available(MetricId.FPR_POPULATION_STANDARD_DEVIATION, std, denominator=len(values)),
    ]
    warnings: tuple[MetricWarning, ...] = ()
    if mean == 0.0:
        metrics.append(
            unavailable(MetricId.FPR_COEFFICIENT_OF_VARIATION, MetricStatus.UNDEFINED, MetricReason.ZERO_MEAN)
        )
    else:
        metrics.append(available(MetricId.FPR_COEFFICIENT_OF_VARIATION, std / mean, denominator=len(values)))
        if mean < NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF.value:
            warnings = (MetricWarning(WarningCode.NEAR_ZERO_MEAN_FPR, MetricId.FPR_COEFFICIENT_OF_VARIATION),)
    q25, q75 = np.quantile(array, (0.25, 0.75), method="linear")
    metrics.extend(
        (
            available(MetricId.FPR_IQR, float(q75 - q25), denominator=len(values)),
            available(MetricId.FPR_RANGE, float(np.max(array) - np.min(array)), denominator=len(values)),
            available(MetricId.WORST_CLIENT_FPR, float(np.max(array)), denominator=len(values)),
        )
    )
    return tuple(metrics), warnings


def _attack_aggregates(results: tuple[ClientMetricResult, ...]) -> tuple[MetricAvailability, ...]:
    tpr = _available_values(results, MetricId.TRUE_POSITIVE_RATE)
    macro = _available_values(results, MetricId.BINARY_MACRO_F1)
    balanced = _available_values(results, MetricId.BALANCED_ACCURACY)
    tpr_cv = _coefficient_of_variation(MetricId.TPR_COEFFICIENT_OF_VARIATION, tpr)
    return (
        tpr_cv,
        _quantile_or_unavailable(MetricId.P10_BINARY_MACRO_F1, macro, Quantile(0.10)),
        _minimum_or_unavailable(MetricId.WORST_CLIENT_BALANCED_ACCURACY, balanced),
        _mean_or_unavailable(MetricId.MEAN_CLIENT_MACRO_F1, macro),
        _pooled_macro_f1_or_unavailable(results),
        _mean_or_unavailable(MetricId.MEAN_CLIENT_BALANCED_ACCURACY, balanced),
    )


def _metric(result: ClientMetricResult, metric: MetricId) -> MetricAvailability:
    for candidate in result.metrics:
        if candidate.metric is metric:
            return candidate
    raise ScientificContractError(f"client result lacks required metric {metric.value}")


def _available_values(results: tuple[ClientMetricResult, ...], metric: MetricId) -> tuple[float, ...]:
    return tuple(record.value.value for result in results if (record := _metric(result, metric)).value is not None)


def _coefficient_of_variation(metric: MetricId, values: tuple[float, ...]) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    mean = float(np.mean(values))
    if mean == 0.0:
        return unavailable(metric, MetricStatus.UNDEFINED, MetricReason.ZERO_MEAN)
    return available(metric, float(np.std(values, ddof=0)) / mean, denominator=len(values))


def _quantile_or_unavailable(metric: MetricId, values: tuple[float, ...], probability: Quantile) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    return available(
        metric, float(np.quantile(np.asarray(values), probability.value, method="linear")), denominator=len(values)
    )


def _minimum_or_unavailable(metric: MetricId, values: tuple[float, ...]) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    return available(metric, min(values), denominator=len(values))


def _mean_or_unavailable(metric: MetricId, values: tuple[float, ...]) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    return available(metric, float(np.mean(values)), denominator=len(values))


def _pooled_macro_f1_or_unavailable(results: tuple[ClientMetricResult, ...]) -> MetricAvailability:
    eligible = tuple(result for result in results if result.confusion.attack_assignment_valid)
    if not eligible:
        return unavailable(MetricId.POOLED_MACRO_F1, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    true_negative = sum(result.confusion.true_negative.value for result in eligible)
    false_positive = sum(result.confusion.false_positive.value for result in eligible)
    true_positive = sum(result.confusion.true_positive.value for result in eligible)
    false_negative = sum(result.confusion.false_negative.value for result in eligible)
    attack_denominator = 2 * true_positive + false_positive + false_negative
    benign_denominator = 2 * true_negative + false_positive + false_negative
    if attack_denominator == 0 or benign_denominator == 0:
        return unavailable(MetricId.POOLED_MACRO_F1, MetricStatus.UNDEFINED, MetricReason.UNDEFINED_CLASS_F1)
    attack_f1 = 2.0 * true_positive / attack_denominator
    benign_f1 = 2.0 * true_negative / benign_denominator
    return available(MetricId.POOLED_MACRO_F1, (attack_f1 + benign_f1) / 2.0)


def _count(value: int) -> RowCount:
    return RowCount(value)
