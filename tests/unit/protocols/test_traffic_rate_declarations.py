from datp_core.domain.enums import MetricId
from datp_core.protocols.metrics import SUPPRESSED_OPERATIONAL_METRICS
from datp_core.protocols.traffic_rates import TRAFFIC_RATE_EVIDENCE


def test_absent_evidence_is_an_immutable_empty_tuple() -> None:
    assert TRAFFIC_RATE_EVIDENCE == ()
    assert SUPPRESSED_OPERATIONAL_METRICS == (MetricId.ALERTS_PER_DAY,)
