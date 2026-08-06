from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.analysis.temporal import TemporalInterpretation, decide_temporal, temporal_recovery
from datp_core.domain.enums import AvailabilityStatus
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue


def test_scientific_decision_member_set_is_exact_and_unique() -> None:
    assert set(ScientificDecision.__members__) == {
        "SUPPORTED",
        "DIRECTIONAL_INCONCLUSIVE",
        "NO_OBSERVED_ADVANTAGE",
        "OPPOSITE_DIRECTION",
        "PARTIAL_ABSORPTION",
        "FULL_ABSORPTION",
        "BOUNDARY_RESULT",
        "INFEASIBLE",
        "BLOCKED",
    }
    values = tuple(member.value for member in ScientificDecision)
    assert len(values) == len(set(values))
    assert all(value.islower() for value in values)


def test_material_drift_with_recovery_is_supported() -> None:
    result = temporal_recovery(
        seed=Seed(1),
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.25),
        recalibrated_future_cv=MetricValue(0.15),
    )
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY
    assert decide_temporal(result).decision is ScientificDecision.SUPPORTED


def test_material_drift_without_recovery_is_a_boundary_result() -> None:
    result = temporal_recovery(
        seed=Seed(2),
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.25),
        recalibrated_future_cv=MetricValue(0.30),
    )
    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY
    assert decide_temporal(result).decision is ScientificDecision.BOUNDARY_RESULT


def test_no_material_degradation_is_not_blocked() -> None:
    result = temporal_recovery(
        seed=Seed(3),
        static_reference_cv=MetricValue(0.20),
        frozen_future_cv=MetricValue(0.30),
        recalibrated_future_cv=MetricValue(0.10),
    )
    assert result.recovery_ratio is None
    assert result.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
    assert decide_temporal(result).decision is ScientificDecision.BOUNDARY_RESULT


def test_opposite_temporal_movement_is_preserved() -> None:
    result = temporal_recovery(
        seed=Seed(4),
        static_reference_cv=MetricValue(0.30),
        frozen_future_cv=MetricValue(0.10),
        recalibrated_future_cv=MetricValue(0.20),
    )
    assert result.interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
    assert decide_temporal(result).decision is ScientificDecision.OPPOSITE_DIRECTION
