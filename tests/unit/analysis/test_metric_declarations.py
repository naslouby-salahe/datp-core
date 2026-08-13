from datp_core.analysis.metrics.protocols import (
    ATTACK_QUALITY_CONTROL_METRICS,
    CONFIRMATORY_METRICS,
    CV_ZERO_MEAN_POLICY,
    NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF,
)
from datp_core.core.identifiers import AvailabilityStatus, MetricId
from datp_core.thresholds.centralized import CENTRALIZED_POOLED_METRICS


def test_metric_semantics_are_explicit() -> None:
    assert CV_ZERO_MEAN_POLICY is AvailabilityStatus.UNDEFINED
    assert MetricId.FPR_IQR in CONFIRMATORY_METRICS
    assert MetricId.FPR_RANGE in CONFIRMATORY_METRICS
    assert MetricId.WORST_CLIENT_FPR in CONFIRMATORY_METRICS
    assert MetricId.P10_BINARY_MACRO_F1 in ATTACK_QUALITY_CONTROL_METRICS
    assert MetricId.AVERAGE_PRECISION in ATTACK_QUALITY_CONTROL_METRICS
    assert MetricId.AVERAGE_PRECISION in CENTRALIZED_POOLED_METRICS
    assert NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF.value == 0.01
