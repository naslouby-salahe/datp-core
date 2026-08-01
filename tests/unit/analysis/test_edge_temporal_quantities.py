from datp_core.analysis.temporal import TemporalInterpretation, temporal_recovery
from datp_core.domain.enums import AvailabilityStatus
from datp_core.domain.values import MetricValue, Seed


def test_recovery_ratio_is_undefined_without_material_drift() -> None:
    result = temporal_recovery(
        seed=Seed(0),
        static_reference_cv=MetricValue(0.2),
        frozen_future_cv=MetricValue(0.3),
        recalibrated_future_cv=MetricValue(0.1),
    )
    assert result.availability is AvailabilityStatus.UNDEFINED
    assert result.recovery_ratio is None
    assert result.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION


def test_negative_recovery_and_opposite_movement_are_visible() -> None:
    negative = temporal_recovery(
        seed=Seed(0),
        static_reference_cv=MetricValue(0.1),
        frozen_future_cv=MetricValue(0.3),
        recalibrated_future_cv=MetricValue(0.4),
    )
    opposite = temporal_recovery(
        seed=Seed(0),
        static_reference_cv=MetricValue(0.3),
        frozen_future_cv=MetricValue(0.1),
        recalibrated_future_cv=MetricValue(0.2),
    )
    assert negative.recovered_amount == MetricValue(-0.10000000000000003)
    assert negative.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY
    assert opposite.interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
