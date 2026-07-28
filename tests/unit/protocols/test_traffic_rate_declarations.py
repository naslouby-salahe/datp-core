from datp_core.protocols.traffic_rates import TRAFFIC_RATE_EVIDENCE


def test_absent_evidence_is_an_immutable_empty_tuple() -> None:
    assert TRAFFIC_RATE_EVIDENCE == ()
