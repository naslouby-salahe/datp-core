from math import isclose

from datp_core.analysis.mechanisms import (
    AssociationObservation,
    DivergenceBlocker,
    ThresholdOperatingPoint,
    blocked_jensen_shannon_divergence,
    decide_model_absorption,
    heterogeneity_benefit_association,
    threshold_movement,
)
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PopulationId,
    PopulationIdentityKind,
    ScientificDecision,
)
from datp_core.domain.values import MetricValue, ThresholdValue
from datp_core.populations.models import ClientIdentity


def test_association_is_associative_and_reports_all_observations() -> None:
    observations = (
        AssociationObservation(heterogeneity=MetricValue(0.1), benefit=MetricValue(0.01)),
        AssociationObservation(heterogeneity=MetricValue(0.3), benefit=MetricValue(0.04)),
        AssociationObservation(heterogeneity=MetricValue(0.7), benefit=MetricValue(0.09)),
    )

    result = heterogeneity_benefit_association(observations)

    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.observations == observations
    assert result.observation_count == 3
    assert result.statistics is not None
    assert result.statistics.regression_slope is not None
    assert len(result.statistics.leverage) == len(observations)


def test_threshold_movement_marks_attack_tradeoff_unavailable_without_attack_assignment() -> None:
    client = ClientIdentity(
        PopulationId.EDGE_SENSOR_GROUPS,
        "sensor_a",
        PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
    )

    result = threshold_movement(
        client=client,
        shared=ThresholdOperatingPoint(
            threshold=ThresholdValue(0.4),
            fpr=MetricValue(0.2),
            tpr=None,
        ),
        local=ThresholdOperatingPoint(
            threshold=ThresholdValue(0.6),
            fpr=MetricValue(0.1),
            tpr=None,
        ),
    )

    assert result.evidence_role is EvidenceRole.MECHANISM
    assert isclose(result.delta_threshold.value, 0.2)
    assert isclose(result.delta_fpr.value, -0.1)
    assert result.delta_tpr is None
    assert result.attack_availability is AvailabilityStatus.UNAVAILABLE


def test_unresolved_jsd_semantics_produce_a_typed_blocker_without_histogram_estimation() -> None:
    clients = (
        ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, "client_a", PopulationIdentityKind.PHYSICAL_DEVICES),
        ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, "client_b", PopulationIdentityKind.PHYSICAL_DEVICES),
    )

    result = blocked_jensen_shannon_divergence(clients, DivergenceBlocker.BINNING_UNRESOLVED)

    assert result.availability is AvailabilityStatus.UNAVAILABLE
    assert result.blocker is DivergenceBlocker.BINNING_UNRESOLVED
    assert result.pairwise_values == ()
    assert result.aggregate is None


def test_model_absorption_blocks_a_nonpositive_fedavg_reference_effect() -> None:
    result = decide_model_absorption(MetricValue(0.0), MetricValue(0.2))

    assert result.decision is ScientificDecision.BLOCKED
    assert result.availability is AvailabilityStatus.UNAVAILABLE
