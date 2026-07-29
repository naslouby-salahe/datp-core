from datp_core.datasets.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.domain.enums import CapabilityStatus


def test_nbaio_capability_boundaries() -> None:
    assert NBAIOT_CAPABILITIES.chronology.status is CapabilityStatus.UNAVAILABLE
    assert NBAIOT_CAPABILITIES.family_taxonomy.status is CapabilityStatus.SUPPORTED
