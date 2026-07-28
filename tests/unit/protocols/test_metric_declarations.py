from datp_core.domain.enums import AvailabilityStatus
from datp_core.protocols.metrics import (
    CONFIRMATORY_METRICS,
    CV_ZERO_MEAN_POLICY,
    NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF,
    TEMPORAL_CV_MATERIALITY_CUTOFF,
)


def test_metric_semantics_are_explicit() -> None:
    assert CV_ZERO_MEAN_POLICY is AvailabilityStatus.UNDEFINED
    assert len(CONFIRMATORY_METRICS) > 0
    assert NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF.value == 0.01
    assert TEMPORAL_CV_MATERIALITY_CUTOFF.value == 0.10
