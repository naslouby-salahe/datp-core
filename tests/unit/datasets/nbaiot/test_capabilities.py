from datp_core.core.identifiers import FederatedThresholdMethod, PopulationId
from datp_core.data.nbaiot.capabilities import NBAIOT_CAPABILITIES
from datp_core.data.populations.contracts import CapabilityStatus
from datp_core.data.registry import population_capabilities


def test_nbaio_capability_boundaries() -> None:
    assert NBAIOT_CAPABILITIES.chronology.status is CapabilityStatus.UNAVAILABLE
    assert NBAIOT_CAPABILITIES.family_taxonomy.status is CapabilityStatus.SUPPORTED


def test_nbaiot_declares_threshold_variants_as_supported() -> None:
    methods = {capability.method: capability.status for capability in NBAIOT_CAPABILITIES.threshold_methods}
    for method in (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.FAMILY_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
    ):
        assert methods[method] is CapabilityStatus.SUPPORTED
    assert methods[FederatedThresholdMethod.CLUSTER_THRESHOLD] is CapabilityStatus.CONDITIONAL
    assert methods[FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE] is CapabilityStatus.SUPPORTED
    valid = population_capabilities(PopulationId.NBAIOT_NATURAL_DEVICES).valid_threshold_methods
    assert FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE in valid
    assert FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE in valid
