"""Capability declaration for the audited Edge-IIoTset artifact."""

from datp_core.datasets.capabilities import (
    AttackAssignmentCapability,
    ChronologyCapability,
    DatasetCapabilities,
    ExternalValidationCapability,
    FamilyTaxonomyCapability,
    MetricCapability,
    PhysicalClientCapability,
    TemporalCapability,
    ThresholdMethodCapability,
)
from datp_core.domain.enums import CapabilityStatus, EvidenceRole, FederatedThresholdMethod, MetricId, PopulationId

from .schema import EDGE_BENIGN_SENSOR_GROUPS, EdgeSensorGroup

EDGE_TEMPORAL_SENSOR_GROUPS = frozenset(EDGE_BENIGN_SENSOR_GROUPS) - frozenset((EdgeSensorGroup.MODBUS,))
_STATIC_SENSOR_GROUP_COUNT = len(EDGE_BENIGN_SENSOR_GROUPS)
_TEMPORAL_SENSOR_GROUP_COUNT = len(EDGE_TEMPORAL_SENSOR_GROUPS)
_TEMPORAL_EXCLUDED_SENSOR_GROUP = EdgeSensorGroup.MODBUS.value

EDGE_IIOTSET_CAPABILITIES = DatasetCapabilities(
    physical_clients=PhysicalClientCapability(
        CapabilityStatus.SUPPORTED,
        f"{_STATIC_SENSOR_GROUP_COUNT} audited normal-traffic sensor folders provide "
        "static benign sensor-group identities.",
        "Identities apply only to benign source folders.",
        tuple(group.value for group in EDGE_BENIGN_SENSOR_GROUPS),
    ),
    family_taxonomy=FamilyTaxonomyCapability(
        CapabilityStatus.UNAVAILABLE,
        "No audited Edge source defines a complete sensor-family taxonomy.",
        "Folder names cannot be used to infer a family taxonomy.",
        (),
    ),
    chronology=ChronologyCapability(
        CapabilityStatus.CONDITIONAL,
        f"{_TEMPORAL_SENSOR_GROUP_COUNT} normal-traffic CSVs align one-to-one with their paired PCAP capture records.",
        "PCAP calendar timestamps are admitted only after a complete per-row alignment check; "
        f"{_TEMPORAL_EXCLUDED_SENSOR_GROUP} remains excluded.",
        tuple(group.value for group in sorted(EDGE_TEMPORAL_SENSOR_GROUPS)),
    ),
    attack_assignment=AttackAssignmentCapability(
        CapabilityStatus.UNAVAILABLE,
        "Attack CSVs have row-level labels but occur outside benign sensor folders.",
        "No audited evidence assigns attack rows to the static benign sensor identities.",
        True,
        False,
    ),
    metrics=MetricCapability(
        CapabilityStatus.CONDITIONAL,
        "Benign sensor-group identity is available for static FPR analysis.",
        "Cross-client attack-sensitive metrics are unavailable because attack assignment is unavailable.",
        (MetricId.FALSE_POSITIVE_RATE, MetricId.FPR_COEFFICIENT_OF_VARIATION),
        (),
        (MetricId.TRUE_POSITIVE_RATE, MetricId.BALANCED_ACCURACY, MetricId.BINARY_MACRO_F1, MetricId.AUROC),
    ),
    temporal=TemporalCapability(
        CapabilityStatus.SUPPORTED,
        f"{_TEMPORAL_SENSOR_GROUP_COUNT} paired CSV-PCAP sensor groups supply verified capture timestamps.",
        "Every publication revalidates PCAP alignment; "
        f"{_TEMPORAL_EXCLUDED_SENSOR_GROUP} stays outside the temporal population.",
        True,
    ),
    external_validation=ExternalValidationCapability(
        CapabilityStatus.SUPPORTED,
        "The scientific source assigns Edge-IIoTset external benign-equity validation.",
        "It cannot establish cross-client attack-detection generalization.",
        (EvidenceRole.EXTERNAL_VALIDATION,),
    ),
    valid_populations=(PopulationId.EDGE_SENSOR_GROUPS, PopulationId.EDGE_TEMPORAL_GROUPS),
    threshold_methods=(
        ThresholdMethodCapability(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "Static benign sensor-group identity is available.",
            "The method is limited to benign external-validation outcomes.",
        ),
        ThresholdMethodCapability(
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "Static benign sensor-group identity is available.",
            "The method is limited to benign external-validation outcomes.",
        ),
    ),
)
