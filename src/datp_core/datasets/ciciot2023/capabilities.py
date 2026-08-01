"""Capability declaration for CICIoT2023's processed merged artifact."""

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

CICIOT2023_CAPABILITIES = DatasetCapabilities(
    physical_clients=PhysicalClientCapability(
        CapabilityStatus.UNAVAILABLE,
        "Merged CSVs preserve source-file identity but no physical-device identifier.",
        "The original topology cannot be reconstructed from the processed artifact.",
        (),
    ),
    family_taxonomy=FamilyTaxonomyCapability(
        CapabilityStatus.UNAVAILABLE,
        "No physical-device identities survive in the merged files.",
        "A device-family taxonomy cannot be derived from filenames or source-paper counts.",
        (),
    ),
    chronology=ChronologyCapability(
        CapabilityStatus.UNAVAILABLE,
        "The 40-column merged schema has no audited capture-time field.",
        "Merged-file ordering is not chronology evidence.",
        (),
    ),
    attack_assignment=AttackAssignmentCapability(
        CapabilityStatus.UNAVAILABLE,
        "The Label field supplies row-level attack labels only.",
        "Rows cannot be assigned to the original physical devices.",
        True,
        False,
    ),
    metrics=MetricCapability(
        CapabilityStatus.CONDITIONAL,
        "The full merged-file audit found nine null labels and 991 infinite Rate values.",
        "Model inputs require the declared exclusion-only gate; raw canonical rows remain lossless and unmodified.",
        (),
        tuple(MetricId),
        (),
    ),
    temporal=TemporalCapability(
        CapabilityStatus.UNAVAILABLE,
        "No source timestamp field is retained in merged files.",
        "Temporal experiments are prohibited.",
        False,
    ),
    external_validation=ExternalValidationCapability(
        CapabilityStatus.SUPPORTED,
        "The scientific source assigns CICIoT2023 a file-defined applicability-boundary role.",
        "The approved outcome-blind eligibility gate must run before file-defined population construction.",
        (EvidenceRole.APPLICABILITY_BOUNDARY,),
    ),
    valid_populations=(PopulationId.CICIOT_FILE_CLIENTS,),
    threshold_methods=(
        ThresholdMethodCapability(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "File-defined pseudo-clients retain benign rows after the declared eligibility gate.",
            "The shared threshold remains an applicability-boundary comparison only.",
        ),
        ThresholdMethodCapability(
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "File-defined pseudo-clients retain benign rows after the declared eligibility gate.",
            "The local threshold remains an applicability-boundary comparison only.",
        ),
        ThresholdMethodCapability(
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
            CapabilityStatus.CONDITIONAL,
            "Taxonomy-free clustering may use benign reconstruction-error summaries.",
            "Execution requires a separately declared, outcome-blind cluster-feasibility criterion after eligibility.",
        ),
    ),
)
