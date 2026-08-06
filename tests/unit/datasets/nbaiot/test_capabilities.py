from datp_core.datasets.capabilities import CapabilityStatus
from datp_core.datasets.nbaiot.capabilities import NBAIOT_CAPABILITIES


def test_nbaio_capability_boundaries() -> None:
    assert NBAIOT_CAPABILITIES.chronology.status is CapabilityStatus.UNAVAILABLE
    assert NBAIOT_CAPABILITIES.family_taxonomy.status is CapabilityStatus.SUPPORTED
