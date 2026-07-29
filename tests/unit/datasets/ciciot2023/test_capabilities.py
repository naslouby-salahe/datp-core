from datp_core.datasets.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.domain.enums import CapabilityStatus, FederatedThresholdMethod, PopulationId


def test_ciciot_physical_identity_is_unavailable() -> None:
    assert CICIOT2023_CAPABILITIES.physical_clients.status is CapabilityStatus.UNAVAILABLE


def test_ciciot_file_boundary_requires_the_model_input_eligibility_gate() -> None:
    assert CICIOT2023_CAPABILITIES.external_validation.status is CapabilityStatus.SUPPORTED
    assert CICIOT2023_CAPABILITIES.valid_populations == (PopulationId.CICIOT_FILE_CLIENTS,)
    assert tuple(capability.method for capability in CICIOT2023_CAPABILITIES.threshold_methods) == (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
    )
