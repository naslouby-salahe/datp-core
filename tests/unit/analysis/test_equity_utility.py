from types import SimpleNamespace
from typing import cast

from datp_core.analysis.mechanisms.equity_utility import (
    ConfirmatoryEquityUtilityMeasure,
    confirmatory_equity_utility_bundle,
    confirmatory_equity_utility_metric,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import AvailableMetric
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue, Seed


def test_confirmatory_equity_utility_bundle_keeps_policy_means_and_paired_difference() -> None:
    bundle = confirmatory_equity_utility_bundle(
        (
            (
                _document(seed=1, method=FederatedThresholdMethod.SHARED_THRESHOLD, offset=1.0),
                _document(seed=1, method=FederatedThresholdMethod.LOCAL_THRESHOLD, offset=0.0),
            ),
            (
                _document(seed=2, method=FederatedThresholdMethod.SHARED_THRESHOLD, offset=3.0),
                _document(seed=2, method=FederatedThresholdMethod.LOCAL_THRESHOLD, offset=1.0),
            ),
        )
    )

    cv = next(item for item in bundle.measures if item.measure is ConfirmatoryEquityUtilityMeasure.CV_FPR)
    target_error = next(
        item
        for item in bundle.measures
        if item.measure is ConfirmatoryEquityUtilityMeasure.MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR
    )

    assert cv.shared_mean is not None and cv.shared_mean.value == 2.0
    assert cv.local_mean is not None and cv.local_mean.value == 0.5
    assert cv.paired_difference_mean is not None and cv.paired_difference_mean.value == -1.5
    assert cv.paired_seed_count.value == 2
    assert target_error.paired_seed_count.value == 2
    assert (
        confirmatory_equity_utility_metric(target_error.measure)
        is MetricId.MEAN_ABSOLUTE_TEST_FPR_TARGET_ERROR
    )


def _document(*, seed: int, method: FederatedThresholdMethod, offset: float) -> FederatedEvaluationDocument:
    metrics = tuple(
        AvailableMetric(metric=metric, value=MetricValue(offset))
        for metric in (
            MetricId.MEAN_FPR,
            MetricId.FPR_COEFFICIENT_OF_VARIATION,
            MetricId.FPR_IQR,
            MetricId.FPR_RANGE,
            MetricId.WORST_CLIENT_FPR,
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BINARY_MACRO_F1,
            MetricId.P10_BINARY_MACRO_F1,
            MetricId.WORST_CLIENT_BALANCED_ACCURACY,
        )
    )
    return cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            threshold_method=method,
            score_coordinate=SimpleNamespace(training_seed=Seed(seed)),
            population=SimpleNamespace(metrics=metrics),
            diagnostics=SimpleNamespace(
                held_out_operating_point_summary=SimpleNamespace(
                    mean_absolute_target_error=MetricValue(offset),
                    mean_absolute_calibration_generalization_gap=MetricValue(offset),
                )
            ),
        ),
    )
