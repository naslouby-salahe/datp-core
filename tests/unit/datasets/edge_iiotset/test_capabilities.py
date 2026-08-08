from datp_core.data.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES


def test_edge_attacks_remain_unassigned() -> None:
    assert EDGE_IIOTSET_CAPABILITIES.attack_assignment.client_level_assignment_available is False
