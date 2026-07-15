import pytest

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
from datp_core.infrastructure.evaluation.metrics import (
    ClusterMetricRequest,
    DetectionQualityMetricRequest,
    DiagnosticMetricRequest,
    DistributionMetricRequest,
    EquityMetricRequest,
    EstimationMetricRequest,
    MetricCalculator,
    OperatingPointMetricRequest,
    ResourceMetricRequest,
)


def test_each_metric_family_has_a_named_known_value_calculation() -> None:
    calculator = MetricCalculator()

    operating = calculator.compute_operating_point(
        OperatingPointMetricRequest(metric=OperatingPointMetric.FPR_RANGE, values=(0.1, 0.4, 0.2), target=None)
    )
    detection = calculator.compute_detection_quality(
        DetectionQualityMetricRequest(metric=DetectionQualityMetric.WORST_CLIENT_BA, values=(0.8, 0.6, 0.9))
    )
    equity = calculator.compute_equity(EquityMetricRequest(metric=EquityMetric.JAIN_INDEX, values=(1.0, 1.0)))
    estimation = calculator.compute_estimation(
        EstimationMetricRequest(metric=EstimationMetric.QUANTILE_ESTIMATION_ERROR, values=(0.2, 0.4), reference=0.3)
    )
    cluster = calculator.compute_cluster(
        ClusterMetricRequest(metric=ClusterMetric.ADJUSTED_RAND_INDEX, values=(1.0, 0.5))
    )
    distribution = calculator.compute_distribution(
        DistributionMetricRequest(metric=DistributionMetric.PAIRWISE_JS_DIVERGENCE, values=(0.1, 0.3))
    )
    diagnostic = calculator.compute_diagnostic(
        DiagnosticMetricRequest(metric=DiagnosticRatio.BETWEEN_RATIO, values=(0.2, 0.4))
    )
    resource = calculator.compute_resource(
        ResourceMetricRequest(metric=ResourceMetric.TOTAL_COMMUNICATION_BYTES, values=(3.0, 5.0))
    )

    assert operating.value == pytest.approx(0.3)
    assert detection.value == 0.6
    assert equity.value == 1.0
    assert estimation.value == pytest.approx(0.1)
    assert cluster.value == 0.75
    assert distribution.value == pytest.approx(0.2)
    assert diagnostic.value == pytest.approx(0.3)
    assert resource.value == 8.0
