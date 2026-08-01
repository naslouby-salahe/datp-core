from datp_core.analysis.temporal import temporal_recovery
from datp_core.domain.enums import AvailabilityStatus
from datp_core.domain.values import MetricValue, Seed


def test_temporal_recovery_requires_strict_positive_materiality_at_the_boundary() -> None:
    result = temporal_recovery(
        seed=Seed(1),
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.20),
        recalibrated_future_cv=MetricValue(0.15),
    )

    assert result.drift_excess.value == 0.10
    assert result.recovery_ratio is None
    assert result.availability is AvailabilityStatus.UNDEFINED


def test_temporal_recovery_preserves_negative_recovery_when_material_drift_exists() -> None:
    result = temporal_recovery(
        seed=Seed(2),
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.25),
        recalibrated_future_cv=MetricValue(0.30),
    )

    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.recovered_amount.value < 0
    assert result.recovery_ratio is not None and result.recovery_ratio.value < 0
