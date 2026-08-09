from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.models import MetricStatus
from datp_core.analysis.operational.alert_burden import AlertBurdenSuppressionReason, calculate_alert_burden
from datp_core.analysis.operational.traffic_rates import (
    TrafficRateGranularity,
    TrafficRateUnit,
    ValidatedTrafficRateEvidence,
)
from datp_core.core.identifiers import (
    PopulationId,
    TrafficRateEvidenceType,
    TrafficRateLocatorText,
    TrafficRateProvenanceText,
)
from datp_core.core.numeric import Ratio, Seed, TrafficRatePerDay


def test_alert_burden_is_suppressed_without_traffic_evidence() -> None:
    result = calculate_alert_burden(
        client=client_identity("client_a"),
        coordinate=fedavg_coordinate(Seed(7)),
        training_seed=Seed(7),
        false_positive_rate=Ratio(0.2),
        evidence=None,
    )

    assert result.suppression_reason is AlertBurdenSuppressionReason.NO_APPLICABLE_TRAFFIC_RATE_EVIDENCE
    assert result.metric.status is MetricStatus.SUPPRESSED
    assert result.alerts_per_client_per_day is None


def test_alert_burden_uses_valid_per_client_rate() -> None:
    evidence = ValidatedTrafficRateEvidence(
        TrafficRateEvidenceType.MEASURED,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrafficRatePerDay(20),
        TrafficRateLocatorText("source"),
        TrafficRateProvenanceText("audit"),
        TrafficRateUnit.BENIGN_DECISIONS_PER_CLIENT_PER_DAY,
        TrafficRateGranularity.PER_CLIENT,
        True,
    )
    result = calculate_alert_burden(
        client=client_identity("client_a"),
        coordinate=fedavg_coordinate(Seed(7)),
        training_seed=Seed(7),
        false_positive_rate=Ratio(0.2),
        evidence=evidence,
    )

    assert result.alerts_per_client_per_day == 4.0
