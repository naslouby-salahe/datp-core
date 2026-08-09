"""Capability declaration for the audited Edge-IIoTset artifact."""

from datp_core.core.identifiers import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)
from datp_core.data.populations.contracts import (
    AttackAssignmentCapability,
    CapabilityStatus,
    ChronologyCapability,
    DatasetCapabilities,
    ExternalValidationCapability,
    FamilyTaxonomyCapability,
    MetricCapability,
    PhysicalClientCapability,
    TemporalCapability,
    ThresholdMethodCapability,
)

from .schema import EDGE_BENIGN_SENSOR_GROUPS, EdgeSensorGroup

EDGE_TEMPORAL_SENSOR_GROUPS = frozenset(EDGE_BENIGN_SENSOR_GROUPS) - frozenset((EdgeSensorGroup.MODBUS,))
_STATIC_SENSOR_GROUP_COUNT = len(EDGE_BENIGN_SENSOR_GROUPS)
_TEMPORAL_SENSOR_GROUP_COUNT = len(EDGE_TEMPORAL_SENSOR_GROUPS)
_TEMPORAL_EXCLUDED_SENSOR_GROUP = EdgeSensorGroup.MODBUS

EDGE_IIOTSET_CAPABILITIES = DatasetCapabilities(
    physical_clients=PhysicalClientCapability(
        CapabilityStatus.SUPPORTED,
        f"{_STATIC_SENSOR_GROUP_COUNT} audited normal-traffic sensor folders provide "
        "static benign sensor-group identities.",
        "Identities apply only to benign source folders.",
        EDGE_BENIGN_SENSOR_GROUPS,
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
        tuple(sorted(EDGE_TEMPORAL_SENSOR_GROUPS)),
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
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible benign sensor groups provide local calibration quantiles.",
            reason="The method is limited to benign external and temporal outcomes.",
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible benign calibration scores can be pooled without using attack-labelled rows.",
            reason="The result remains a shared-threshold external comparator, not a centralized detector.",
            method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible local benign thresholds and support counts are available.",
            reason="The method is limited to benign external-validation outcomes.",
            method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible benign sensor groups retain client-local calibration scores.",
            reason="The method is limited to benign external and temporal outcomes.",
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.CONDITIONAL,
            evidence="Eligible clients can be grouped from benign reconstruction-error fingerprints.",
            reason="Execution requires the locked group count to be smaller than the eligible population.",
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Shared and local benign thresholds are available under one frozen detector.",
            reason="Only the predeclared fixed shrinkage curve is supported.",
            method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=(
                "Eligible clients can publish benign-only summary statistics under the declared comparator protocol."
            ),
            reason="The method does not imply formal privacy or attack-sensitive validation.",
            method=FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
        ),
    ),
)
