"""Capability declaration for the audited N-BaIoT artifact."""

from datp_core.core.identifiers import (
    ClientIdentityToken,
    EvidenceRole,
    FamilyIdentity,
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

from .schema import NBAIOT_DEVICE_FAMILIES, NBAIOT_DEVICE_IDENTITIES

_PHYSICAL_CLIENT_IDENTITIES = tuple(ClientIdentityToken(device.value) for device in NBAIOT_DEVICE_IDENTITIES)
_FAMILY_IDENTITIES = tuple(FamilyIdentity(family.value) for family in NBAIOT_DEVICE_FAMILIES)

NBAIOT_CAPABILITIES = DatasetCapabilities(
    physical_clients=PhysicalClientCapability(
        CapabilityStatus.SUPPORTED,
        "Nine audited top-level device folders are preserved in every accepted source path.",
        "N-BaIoT physical-device folders provide defensible natural client identities.",
        _PHYSICAL_CLIENT_IDENTITIES,
    ),
    family_taxonomy=FamilyTaxonomyCapability(
        CapabilityStatus.SUPPORTED,
        "N-BaIoT Table III defines the device type for each of the nine audited devices.",
        "The source-defined device-type mapping is fixed before evaluation and persisted with each canonical row.",
        _FAMILY_IDENTITIES,
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
            status=CapabilityStatus.SUPPORTED,
            evidence="Every audited physical device has benign data.",
            reason="Shared calibration is a declared threshold scope.",
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Every audited physical device has benign data.",
            reason="Local calibration is a declared threshold scope.",
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="N-BaIoT Table III supplies the complete device-family taxonomy.",
            reason="Family calibration uses the source-defined membership only.",
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.CONDITIONAL,
            evidence="Taxonomy-free clustering may use benign reconstruction-error summaries.",
            reason="Execution requires the declared outcome-blind cluster-feasibility criterion.",
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible clients supply benign calibration scores for pooled quantile construction.",
            reason="Pooled shared quantile is a shared-construction control for the natural-device population.",
            method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible clients supply benign calibration counts for sample-weighted shared construction.",
            reason="Sample-weighted shared threshold is a shared-construction control for natural devices.",
            method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Shared and local endpoints are available under one frozen detector.",
            reason="The predeclared fixed-lambda shrinkage curve is supported for the natural-device population.",
            method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible clients supply ordered benign calibration scores for finite-sample conformal ranks.",
            reason="Local conformal threshold is a supportive coverage diagnostic for the natural-device population.",
            method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence="Eligible clients can publish benign-only summary statistics under the declared comparator.",
            reason="Federated benign-statistics is a threshold-variant comparator for the natural-device population.",
            method=FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.UNSUPPORTED,
            evidence="No pre-declared monotone lambda(n_k) function is frozen for this programme.",
            reason=(
                "Size-aware shrinkage remains intentionally unavailable until a bounded "
                "lambda(n_k) is declared before evaluation; inventing a formula is forbidden."
            ),
            method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        ),
    ),
)
