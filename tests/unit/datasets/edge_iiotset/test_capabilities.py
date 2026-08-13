from datp_core.core.identifiers import MetricId
from datp_core.data.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.data.populations.contracts import CapabilityStatus


def test_edge_attacks_remain_unassigned() -> None:
    assert EDGE_IIOTSET_CAPABILITIES.attack_assignment.client_level_assignment_available is False


def test_edge_average_precision_is_unavailable_without_attack_assignment() -> None:
    assert EDGE_IIOTSET_CAPABILITIES.metrics.status_for(MetricId.AVERAGE_PRECISION) is CapabilityStatus.UNAVAILABLE
