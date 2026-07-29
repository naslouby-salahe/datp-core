from datp_core.datasets.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.datasets.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.datasets.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.domain.enums import CapabilityStatus, PopulationId


def test_physical_identity_and_attack_assignment_boundaries() -> None:
    assert NBAIOT_CAPABILITIES.physical_clients.status is CapabilityStatus.SUPPORTED
    assert NBAIOT_CAPABILITIES.attack_assignment.client_level_assignment_available is True
    assert CICIOT2023_CAPABILITIES.physical_clients.status is CapabilityStatus.UNAVAILABLE
    assert EDGE_IIOTSET_CAPABILITIES.attack_assignment.client_level_assignment_available is False


def test_audited_data_quality_and_chronology_limits_are_typed() -> None:
    assert CICIOT2023_CAPABILITIES.metrics.status is CapabilityStatus.CONDITIONAL
    assert CICIOT2023_CAPABILITIES.valid_populations == (PopulationId.CICIOT_FILE_CLIENTS,)
    assert EDGE_IIOTSET_CAPABILITIES.chronology.status is CapabilityStatus.CONDITIONAL
    assert EDGE_IIOTSET_CAPABILITIES.temporal.supports_one_shot_recalibration is True
