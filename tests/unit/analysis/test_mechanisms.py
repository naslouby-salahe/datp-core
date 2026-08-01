from math import isclose

from datp_core.analysis.mechanisms import heterogeneity_benefit_association, threshold_movement
from datp_core.domain.enums import AvailabilityStatus, PopulationId, PopulationIdentityKind
from datp_core.domain.values import MetricValue, ThresholdValue
from datp_core.populations.models import ClientIdentity


def test_association_is_associative_and_reports_all_observations() -> None:
    observations = ((0.1, 0.01), (0.3, 0.04), (0.7, 0.09))

    result = heterogeneity_benefit_association(observations)

    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.observations == observations
    assert result.observation_count == 3
    assert result.slope is not None
    assert len(result.leverage) == len(observations)


def test_threshold_movement_marks_attack_tradeoff_unavailable_without_attack_assignment() -> None:
    client = ClientIdentity(
        PopulationId.EDGE_SENSOR_GROUPS,
        "sensor_a",
        PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
    )

    result = threshold_movement(
        client=client,
        shared_threshold=ThresholdValue(0.4),
        local_threshold=ThresholdValue(0.6),
        shared_fpr=MetricValue(0.2),
        local_fpr=MetricValue(0.1),
        shared_tpr=None,
        local_tpr=None,
    )

    assert isclose(result.delta_threshold.value, 0.2)
    assert isclose(result.delta_fpr.value, -0.1)
    assert result.delta_tpr is None
    assert result.attack_availability is AvailabilityStatus.UNAVAILABLE
