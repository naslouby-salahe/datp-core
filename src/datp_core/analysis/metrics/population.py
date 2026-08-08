import numpy as np

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.models import (
    EQUITY_INDEX_METRIC_IDS,
    FPR_POPULATION_METRIC_IDS,
    ClientMetricResult,
    MetricAvailability,
    MetricReason,
    MetricStatus,
    MetricWarning,
    PopulationMetricAggregates,
    PopulationMetricResult,
    WarningCode,
)
from datp_core.analysis.metrics.semantics import available, unavailable
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import EvaluationCohort, MetricId
from datp_core.core.numeric import MetricValue, Quantile, RowCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.protocols.metrics import NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF


def calculate_population_metrics(
    results: tuple[ClientMetricResult, ...],
    *,
    cohort: EvaluationCohortManifest | None = None,
) -> PopulationMetricResult:
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

    fpr_evaluable: list[ClientMetricResult] = []
    fpr_values: list[MetricValue] = []
    excluded_clients: list[ClientIdentity] = []
    attack_evaluable_count = 0
    fallback_count = 0
    unavailable_count = 0

    for result in results:
        if result.cohort is EvaluationCohort.FPR_EVALUABLE:
            fpr_evaluable.append(result)
            if result.attack_evaluable:
                attack_evaluable_count += 1

            fpr_record = next((m for m in result.metrics if m.metric is MetricId.FALSE_POSITIVE_RATE), None)
            if not fpr_record:
                msg = f"client result lacks required metric {MetricId.FALSE_POSITIVE_RATE.value}"
                raise ScientificContractError(msg)
            if fpr_record.value is not None:
                fpr_values.append(fpr_record.value)
        else:
            excluded_clients.append(result.client)
            if result.cohort is EvaluationCohort.DEPLOYMENT_FALLBACK:
                fallback_count += 1
            elif result.cohort is EvaluationCohort.UNAVAILABLE:
                unavailable_count += 1

    fpr_evaluable_tuple = tuple(fpr_evaluable)
    fpr_values_tuple = tuple(fpr_values)

    if cohort is None:
        calibration_eligible_count = len(fpr_evaluable)
    else:
        calibration_eligible_count = sum(1 for record in cohort.records if record.calibration_eligible)

    aggregates = _population_metric_records(fpr_evaluable_tuple, fpr_values_tuple)

    return PopulationMetricResult(
        coordinate=first.coordinate,
        threshold_method=first.threshold_method,
        cohort=EvaluationCohort.FPR_EVALUABLE,
        metrics=aggregates.metrics,
        candidate_client_count=RowCount(len(results)),
        calibration_eligible_client_count=RowCount(calibration_eligible_count),
        fpr_evaluable_client_count=RowCount(len(fpr_values)),
        attack_evaluable_client_count=RowCount(attack_evaluable_count),
        deployment_fallback_count=RowCount(fallback_count),
        unavailable_client_count=RowCount(unavailable_count),
        excluded_clients=tuple(sorted(excluded_clients, key=lambda item: item.client_id)),
        warnings=aggregates.warnings,
        evidence_role=first.evidence_role,
    )


def _population_metric_records(
    results: tuple[ClientMetricResult, ...], fpr_values: tuple[MetricValue, ...]
) -> PopulationMetricAggregates:
    fpr_aggregates = _fpr_aggregates(fpr_values)
    return PopulationMetricAggregates(
        metrics=(*fpr_aggregates.metrics, *_attack_aggregates(results)),
        warnings=fpr_aggregates.warnings,
    )


def _fpr_aggregates(
    values: tuple[MetricValue, ...],
) -> PopulationMetricAggregates:
    if not values:
        absent = tuple(
            unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
            for metric in (*FPR_POPULATION_METRIC_IDS, *EQUITY_INDEX_METRIC_IDS)
        )
        return PopulationMetricAggregates(metrics=absent, warnings=())
    array = np.fromiter((v.value for v in values), dtype=np.float64, count=len(values))
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
    metrics.extend(_equity_index_metrics(array))
    return PopulationMetricAggregates(metrics=tuple(metrics), warnings=warnings)


def _equity_index_metrics(values: np.ndarray) -> tuple[MetricAvailability, ...]:
    total = float(np.sum(values))
    count = int(values.size)
    if total == 0.0:
        return (
            unavailable(MetricId.JAIN_FAIRNESS_INDEX, MetricStatus.UNDEFINED, MetricReason.ZERO_MEAN),
            unavailable(MetricId.GINI_COEFFICIENT, MetricStatus.UNDEFINED, MetricReason.ZERO_MEAN),
        )
    sum_squares = float(np.sum(values * values))
    jain = (total * total) / (count * sum_squares)
    ordered = np.sort(values)
    ranks = np.arange(1, count + 1, dtype=np.float64)
    gini = (2.0 * float(np.sum(ranks * ordered)) / (count * total)) - ((count + 1.0) / count)
    return (
        available(MetricId.JAIN_FAIRNESS_INDEX, jain, denominator=count),
        available(MetricId.GINI_COEFFICIENT, gini, denominator=count),
    )


def _attack_aggregates(results: tuple[ClientMetricResult, ...]) -> tuple[MetricAvailability, ...]:
    tpr_vals: list[MetricValue] = []
    macro_vals: list[MetricValue] = []
    balanced_vals: list[MetricValue] = []

    for result in results:
        metric_map = {m.metric: m for m in result.metrics}

        for metric_id, val_list in (
            (MetricId.TRUE_POSITIVE_RATE, tpr_vals),
            (MetricId.BINARY_MACRO_F1, macro_vals),
            (MetricId.BALANCED_ACCURACY, balanced_vals),
        ):
            record = metric_map.get(metric_id)
            if not record:
                raise ScientificContractError(f"client result lacks required metric {metric_id.value}")
            if record.value is not None:
                val_list.append(record.value)

    tpr_tuple = tuple(tpr_vals)
    macro_tuple = tuple(macro_vals)
    balanced_tuple = tuple(balanced_vals)

    return (
        _coefficient_of_variation(MetricId.TPR_COEFFICIENT_OF_VARIATION, tpr_tuple),
        _quantile_or_unavailable(MetricId.P10_BINARY_MACRO_F1, macro_tuple, Quantile(0.10)),
        _minimum_or_unavailable(MetricId.WORST_CLIENT_BALANCED_ACCURACY, balanced_tuple),
        _mean_or_unavailable(MetricId.MEAN_CLIENT_MACRO_F1, macro_tuple),
        _pooled_macro_f1_or_unavailable(results),
        _mean_or_unavailable(MetricId.MEAN_CLIENT_BALANCED_ACCURACY, balanced_tuple),
    )


def _coefficient_of_variation(metric: MetricId, values: tuple[MetricValue, ...]) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    raw = np.fromiter((v.value for v in values), dtype=np.float64, count=len(values))
    mean = float(np.mean(raw))
    if mean == 0.0:
        return unavailable(metric, MetricStatus.UNDEFINED, MetricReason.ZERO_MEAN)
    return available(metric, float(np.std(raw, ddof=0)) / mean, denominator=len(values))


def _quantile_or_unavailable(
    metric: MetricId, values: tuple[MetricValue, ...], probability: Quantile
) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    raw = np.fromiter((v.value for v in values), dtype=np.float64, count=len(values))
    return available(metric, float(np.quantile(raw, probability.value, method="linear")), denominator=len(values))


def _minimum_or_unavailable(metric: MetricId, values: tuple[MetricValue, ...]) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    return available(metric, min(v.value for v in values), denominator=len(values))


def _mean_or_unavailable(metric: MetricId, values: tuple[MetricValue, ...]) -> MetricAvailability:
    if not values:
        return unavailable(metric, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)
    raw = np.fromiter((v.value for v in values), dtype=np.float64, count=len(values))
    return available(metric, float(np.mean(raw)), denominator=len(values))


def _pooled_macro_f1_or_unavailable(results: tuple[ClientMetricResult, ...]) -> MetricAvailability:
    eligible_count = 0
    true_negative = false_positive = true_positive = false_negative = 0

    for result in results:
        if result.confusion.attack_assignment_valid:
            eligible_count += 1
            true_negative += result.confusion.true_negative.value
            false_positive += result.confusion.false_positive.value
            true_positive += result.confusion.true_positive.value
            false_negative += result.confusion.false_negative.value

    if not eligible_count:
        return unavailable(MetricId.POOLED_MACRO_F1, MetricStatus.UNAVAILABLE, MetricReason.NO_EVALUABLE_CLIENTS)

    attack_denominator = 2 * true_positive + false_positive + false_negative
    benign_denominator = 2 * true_negative + false_positive + false_negative

    if attack_denominator == 0 or benign_denominator == 0:
        return unavailable(MetricId.POOLED_MACRO_F1, MetricStatus.UNDEFINED, MetricReason.UNDEFINED_CLASS_F1)

    attack_f1 = 2.0 * true_positive / attack_denominator
    benign_f1 = 2.0 * true_negative / benign_denominator

    return available(MetricId.POOLED_MACRO_F1, (attack_f1 + benign_f1) / 2.0)
