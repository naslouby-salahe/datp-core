from enum import StrEnum

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue, Seed, SeedObservationCount


class ConfirmatoryEquityUtilityMeasure(StrEnum):
    MEAN_FPR = "mean_fpr"
    CV_FPR = "cv_fpr"
    IQR_FPR = "iqr_fpr"
    RANGE_FPR = "range_fpr"
    WORST_CLIENT_FPR = "worst_client_fpr"
    TPR = "tpr"
    MACRO_F1 = "macro_f1"
    P10_MACRO_F1 = "p10_macro_f1"
    WORST_CLIENT_BALANCED_ACCURACY = "worst_client_balanced_accuracy"
    MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR = "mean_absolute_test_fpr_target_error"
    MEAN_ABSOLUTE_CALIBRATION_GENERALIZATION_GAP = "mean_absolute_calibration_generalization_gap"


class EquityUtilitySeedObservation(StrictModel):
    seed: Seed
    shared: MetricValue | None
    local: MetricValue | None
    local_minus_shared: MetricValue | None


class EquityUtilityMeasureSummary(StrictModel):
    measure: ConfirmatoryEquityUtilityMeasure
    seed_observations: tuple[EquityUtilitySeedObservation, ...]
    shared_mean: MetricValue | None
    local_mean: MetricValue | None
    paired_difference_mean: MetricValue | None
    paired_seed_count: SeedObservationCount


class ConfirmatoryEquityUtilityBundle(StrictModel):
    shared_method: FederatedThresholdMethod
    local_method: FederatedThresholdMethod
    measures: tuple[EquityUtilityMeasureSummary, ...]


_POPULATION_METRICS: dict[ConfirmatoryEquityUtilityMeasure, MetricId] = {
    ConfirmatoryEquityUtilityMeasure.MEAN_FPR: MetricId.MEAN_FPR,
    ConfirmatoryEquityUtilityMeasure.CV_FPR: MetricId.FPR_COEFFICIENT_OF_VARIATION,
    ConfirmatoryEquityUtilityMeasure.IQR_FPR: MetricId.FPR_IQR,
    ConfirmatoryEquityUtilityMeasure.RANGE_FPR: MetricId.FPR_RANGE,
    ConfirmatoryEquityUtilityMeasure.WORST_CLIENT_FPR: MetricId.WORST_CLIENT_FPR,
    ConfirmatoryEquityUtilityMeasure.TPR: MetricId.TRUE_POSITIVE_RATE,
    ConfirmatoryEquityUtilityMeasure.MACRO_F1: MetricId.BINARY_MACRO_F1,
    ConfirmatoryEquityUtilityMeasure.P10_MACRO_F1: MetricId.P10_BINARY_MACRO_F1,
    ConfirmatoryEquityUtilityMeasure.WORST_CLIENT_BALANCED_ACCURACY: MetricId.WORST_CLIENT_BALANCED_ACCURACY,
    ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR: MetricId.MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR,
    ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_CALIBRATION_GENERALIZATION_GAP: (
        MetricId.MEAN_ABSOLUTE_CALIBRATION_GENERALIZATION_GAP
    ),
}


def confirmatory_equity_utility_metric(measure: ConfirmatoryEquityUtilityMeasure) -> MetricId:
    return _POPULATION_METRICS[measure]


def confirmatory_equity_utility_bundle(
    pairs: tuple[tuple[FederatedEvaluationDocument, FederatedEvaluationDocument], ...],
) -> ConfirmatoryEquityUtilityBundle:
    if not pairs:
        raise ValueError("confirmatory equity-utility bundle requires paired policy evaluations")
    if any(
        shared.threshold_method is not FederatedThresholdMethod.SHARED_THRESHOLD
        or local.threshold_method is not FederatedThresholdMethod.LOCAL_THRESHOLD
        or shared.score_coordinate.training_seed != local.score_coordinate.training_seed
        for shared, local in pairs
    ):
        raise ValueError("equity-utility bundle requires paired shared/local documents for the same seed")
    seeds = tuple(shared.score_coordinate.training_seed for shared, _ in pairs)
    if len(seeds) != len(frozenset(seeds)):
        raise ValueError("equity-utility bundle requires unique seeds")
    return ConfirmatoryEquityUtilityBundle(
        shared_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        local_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        measures=tuple(_measure_summary(measure, pairs) for measure in ConfirmatoryEquityUtilityMeasure),
    )


def _measure_summary(
    measure: ConfirmatoryEquityUtilityMeasure,
    pairs: tuple[tuple[FederatedEvaluationDocument, FederatedEvaluationDocument], ...],
) -> EquityUtilityMeasureSummary:
    observations = tuple(_seed_observation(measure, shared, local) for shared, local in pairs)
    shared_values = tuple(item.shared.value for item in observations if item.shared is not None)
    local_values = tuple(item.local.value for item in observations if item.local is not None)
    differences = tuple(item.local_minus_shared.value for item in observations if item.local_minus_shared is not None)
    return EquityUtilityMeasureSummary(
        measure=measure,
        seed_observations=observations,
        shared_mean=_mean_or_none(shared_values),
        local_mean=_mean_or_none(local_values),
        paired_difference_mean=_mean_or_none(differences),
        paired_seed_count=SeedObservationCount(len(differences)),
    )


def _seed_observation(
    measure: ConfirmatoryEquityUtilityMeasure,
    shared: FederatedEvaluationDocument,
    local: FederatedEvaluationDocument,
) -> EquityUtilitySeedObservation:
    shared_value = _measure_value(measure, shared)
    local_value = _measure_value(measure, local)
    return EquityUtilitySeedObservation(
        seed=shared.score_coordinate.training_seed,
        shared=shared_value,
        local=local_value,
        local_minus_shared=(
            None if shared_value is None or local_value is None else MetricValue(local_value.value - shared_value.value)
        ),
    )


def _measure_value(
    measure: ConfirmatoryEquityUtilityMeasure, document: FederatedEvaluationDocument
) -> MetricValue | None:
    if measure in _POPULATION_METRICS and measure not in {
        ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR,
        ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_CALIBRATION_GENERALIZATION_GAP,
    }:
        metric = _POPULATION_METRICS[measure]
        result = metric_by_id(document.population.metrics, metric)
        return result.value if result.status is MetricStatus.AVAILABLE else None
    summary = document.diagnostics.held_out_operating_point_summary
    if summary is None:
        return None
    if measure is ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR:
        return summary.mean_absolute_target_error
    if measure is ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_CALIBRATION_GENERALIZATION_GAP:
        return summary.mean_absolute_calibration_generalization_gap
    raise ValueError(f"unsupported equity-utility measure: {measure.value}")


def _mean_or_none(values: tuple[float, ...]) -> MetricValue | None:
    return None if not values else MetricValue(sum(values) / len(values))
