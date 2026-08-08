from datp_core.core.identifiers import PopulationId
from datp_core.data.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.data.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.data.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.data.populations.contracts import CapabilityStatus


def test_capability_status_member_set_is_exact_and_unique() -> None:
    assert set(CapabilityStatus.__members__) == {
        "SUPPORTED",
        "UNSUPPORTED",
        "CONDITIONAL",
        "UNAVAILABLE",
        "NOT_APPLICABLE",
    }
    values = tuple(member.value for member in CapabilityStatus)
    assert len(values) == len(set(values))
    assert all(value.islower() for value in values)


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
