from datp_core.core.identifiers import TemporalState


def test_temporal_state_names_do_not_claim_continuous_adaptation() -> None:
    assert all("continuous" not in state.value and "stream" not in state.value for state in TemporalState)
