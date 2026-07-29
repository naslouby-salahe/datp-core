"""Capability declaration for the audited N-BaIoT artifact."""

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
from datp_core.domain.enums import (
    CapabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)

from .schema import NBAIOT_DEVICE_FAMILIES, NBAIOT_DEVICE_IDENTITIES

NBAIOT_CAPABILITIES = DatasetCapabilities(
    physical_clients=PhysicalClientCapability(
        CapabilityStatus.SUPPORTED,
        "Nine audited top-level device folders are preserved in every accepted source path.",
        "N-BaIoT physical-device folders provide defensible natural client identities.",
        NBAIOT_DEVICE_IDENTITIES,
    ),
    family_taxonomy=FamilyTaxonomyCapability(
        CapabilityStatus.SUPPORTED,
        "N-BaIoT Table III defines the device type for each of the nine audited devices.",
        "The source-defined device-type mapping is fixed before evaluation and persisted with each canonical row.",
        NBAIOT_DEVICE_FAMILIES,
    ),
    chronology=ChronologyCapability(
        CapabilityStatus.UNAVAILABLE,
        "Accepted N-BaIoT CSVs have no audited capture-time field.",
        "Source order and file names are not chronology evidence.",
        (),
    ),
    attack_assignment=AttackAssignmentCapability(
        CapabilityStatus.SUPPORTED,
        "Attack family and subtype occur below the same audited device directory as each attack CSV.",
        "Attack records can be assigned to their audited physical-device source identity.",
        True,
        True,
    ),
    metrics=MetricCapability(
        CapabilityStatus.SUPPORTED,
        "Per-device benign and attack source identities are available.",
        "FPR and attack-sensitive metrics remain denominator-dependent at evaluation time.",
        (
            MetricId.FALSE_POSITIVE_RATE,
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BALANCED_ACCURACY,
            MetricId.BINARY_MACRO_F1,
            MetricId.AUROC,
            MetricId.FPR_COEFFICIENT_OF_VARIATION,
        ),
        (),
        (),
    ),
    temporal=TemporalCapability(
        CapabilityStatus.UNAVAILABLE,
        "No audited genuine timestamp field is present in the accepted sources.",
        "Temporal populations cannot be built from source order.",
        False,
    ),
    external_validation=ExternalValidationCapability(
        CapabilityStatus.NOT_APPLICABLE,
        "The scientific source identifies N-BaIoT as the confirmatory physical-device anchor.",
        "It is not an external-validation dataset.",
        (EvidenceRole.CONFIRMATORY,),
    ),
    valid_populations=(PopulationId.NBAIOT_NATURAL_DEVICES, PopulationId.NBAIOT_DIRICHLET_CLIENTS),
    threshold_methods=(
        ThresholdMethodCapability(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "Every audited physical device has benign data.",
            "Shared calibration is a declared threshold scope.",
        ),
        ThresholdMethodCapability(
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "Every audited physical device has benign data.",
            "Local calibration is a declared threshold scope.",
        ),
        ThresholdMethodCapability(
            FederatedThresholdMethod.FAMILY_THRESHOLD,
            CapabilityStatus.SUPPORTED,
            "N-BaIoT Table III supplies the complete device-family taxonomy.",
            "Family calibration uses the source-defined membership only.",
        ),
        ThresholdMethodCapability(
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
            CapabilityStatus.CONDITIONAL,
            "The scientific roadmap defines taxonomy-free clustering from benign reconstruction-error summaries.",
            "Execution requires the declared outcome-blind cluster-feasibility criterion.",
        ),
    ),
)
