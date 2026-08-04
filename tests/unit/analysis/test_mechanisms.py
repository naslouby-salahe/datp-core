from math import isclose

import pytest

from datp_core.analysis.mechanisms import (
    AssociationObservation,
    ClusterPartitionSummary,
    ClusterStabilityResult,
    DivergenceBlocker,
    GroupDispersionObservation,
    ThresholdOperatingPoint,
    blocked_jensen_shannon_divergence,
    decide_model_absorption,
    grouped_dispersion,
    heterogeneity_benefit_association,
    threshold_movement,
)
from datp_core.analysis.models import CorrelationCoefficient
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PopulationId,
    PopulationIdentityKind,
    ScientificDecision,
)
from datp_core.domain.values import ClusterIndex, MetricValue, PairedObservationCount, Ratio, ThresholdValue
from datp_core.populations.models import ClientIdentity


def test_association_reports_all_observations_with_typed_statistics() -> None:
    observations = (
        AssociationObservation(heterogeneity=MetricValue(0.1), benefit=MetricValue(0.01)),
        AssociationObservation(heterogeneity=MetricValue(0.3), benefit=MetricValue(0.04)),
        AssociationObservation(heterogeneity=MetricValue(0.7), benefit=MetricValue(0.09)),
    )
    result = heterogeneity_benefit_association(observations)
    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.observation_count == PairedObservationCount(3)
    assert result.statistics is not None
    assert isinstance(result.statistics.spearman_rho, CorrelationCoefficient)


def test_grouped_dispersion_has_one_typed_result_per_group() -> None:
    result = grouped_dispersion(
        (
            GroupDispersionObservation(
                group_index=ClusterIndex(0),
                thresholds=(ThresholdValue(0.2), ThresholdValue(0.4)),
                false_positive_rates=(Ratio(0.1), Ratio(0.2)),
            ),
            GroupDispersionObservation(
                group_index=ClusterIndex(1),
                thresholds=(ThresholdValue(0.6),),
                false_positive_rates=(Ratio(0.05),),
            ),
        )
    )
    assert result.evidence_role is EvidenceRole.MECHANISM
    assert result.availability is AvailabilityStatus.AVAILABLE
    assert result.group_sizes == (PairedObservationCount(2), PairedObservationCount(1))
    assert result.singleton_groups == (ClusterIndex(1),)
    assert result.across_group_threshold_spread is not None
    assert isclose(result.across_group_threshold_spread.value, 0.3)


def test_cluster_stability_validates_contingency_margins() -> None:
    client_a = _client("a")
    client_b = _client("b")
    with pytest.raises(ValueError, match="row totals"):
        ClusterStabilityResult(
            adjusted_rand_index=CorrelationCoefficient(1.0),
            compared_clients=(client_a, client_b),
            left_partition=ClusterPartitionSummary(group_sizes=(PairedObservationCount(1), PairedObservationCount(1))),
            right_partition=ClusterPartitionSummary(group_sizes=(PairedObservationCount(1), PairedObservationCount(1))),
            contingency=(
                (PairedObservationCount(0), PairedObservationCount(0)),
                (PairedObservationCount(1), PairedObservationCount(1)),
            ),
        )


def test_threshold_movement_marks_attack_tradeoff_unavailable_without_attack_assignment() -> None:
    result = threshold_movement(
        client=_client("sensor_a", PopulationId.EDGE_SENSOR_GROUPS),
        shared=ThresholdOperatingPoint(threshold=ThresholdValue(0.4), fpr=Ratio(0.2), tpr=None),
        local=ThresholdOperatingPoint(threshold=ThresholdValue(0.6), fpr=Ratio(0.1), tpr=None),
    )
    assert isclose(result.delta_threshold.value, 0.2)
    assert isclose(result.delta_fpr.value, -0.1)
    assert result.attack_availability is AvailabilityStatus.UNAVAILABLE


def test_unresolved_jsd_and_absorption_remain_typed() -> None:
    clients = (_client("a"), _client("b"))
    divergence = blocked_jensen_shannon_divergence(clients, DivergenceBlocker.BINNING_UNRESOLVED)
    absorption = decide_model_absorption(MetricValue(0.0), MetricValue(0.2))
    assert divergence.availability is AvailabilityStatus.UNAVAILABLE
    assert absorption.decision is ScientificDecision.BLOCKED


def _client(client_id: str, population: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES) -> ClientIdentity:
    kind = (
        PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS
        if population is PopulationId.EDGE_SENSOR_GROUPS
        else PopulationIdentityKind.PHYSICAL_DEVICES
    )
    return ClientIdentity(population, client_id, kind)
