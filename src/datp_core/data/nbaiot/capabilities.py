from datp_core.core.identifiers import (
    ClientIdentityToken,
    EvidenceRole,
    FamilyIdentity,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    ValidationReasonText,
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
        ValidationReasonText("Nine audited top-level device folders are preserved in every accepted source path."),
        ValidationReasonText("N-BaIoT physical-device folders provide defensible natural client identities."),
        _PHYSICAL_CLIENT_IDENTITIES,
    ),
    family_taxonomy=FamilyTaxonomyCapability(
        CapabilityStatus.SUPPORTED,
        ValidationReasonText("N-BaIoT Table III defines the device type for each of the nine audited devices."),
        ValidationReasonText(
            "The source-defined device-type mapping is fixed before evaluation and persisted with each canonical row.",
        ),
        _FAMILY_IDENTITIES,
    ),
    chronology=ChronologyCapability(
        CapabilityStatus.UNAVAILABLE,
        ValidationReasonText("Accepted N-BaIoT CSVs have no audited capture-time field."),
        ValidationReasonText("Source order and file names are not chronology evidence."),
        (),
    ),
    attack_assignment=AttackAssignmentCapability(
        CapabilityStatus.SUPPORTED,
        ValidationReasonText(
            "Attack family and subtype occur below the same audited device directory as each attack CSV.",
        ),
        ValidationReasonText("Attack records can be assigned to their audited physical-device source identity."),
        True,
        True,
    ),
    metrics=MetricCapability(
        CapabilityStatus.SUPPORTED,
        ValidationReasonText("Per-device benign and attack source identities are available."),
        ValidationReasonText("FPR and attack-sensitive metrics remain denominator-dependent at evaluation time."),
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
        ValidationReasonText("No audited genuine timestamp field is present in the accepted sources."),
        ValidationReasonText("Temporal populations cannot be built from source order."),
        False,
    ),
    external_validation=ExternalValidationCapability(
        CapabilityStatus.NOT_APPLICABLE,
        ValidationReasonText("The scientific source identifies N-BaIoT as the confirmatory physical-device anchor."),
        ValidationReasonText("It is not an external-validation dataset."),
        (EvidenceRole.CONFIRMATORY,),
    ),
    valid_populations=(PopulationId.NBAIOT_NATURAL_DEVICES, PopulationId.NBAIOT_DIRICHLET_CLIENTS),
    threshold_methods=(
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText("Every audited physical device has benign data."),
            reason=ValidationReasonText("Shared calibration is a declared threshold scope."),
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText("Every audited physical device has benign data."),
            reason=ValidationReasonText("Local calibration is a declared threshold scope."),
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText("N-BaIoT Table III supplies the complete device-family taxonomy."),
            reason=ValidationReasonText("Family calibration uses the source-defined membership only."),
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.CONDITIONAL,
            evidence=ValidationReasonText("Taxonomy-free clustering may use benign reconstruction-error summaries."),
            reason=ValidationReasonText("Execution requires the declared outcome-blind cluster-feasibility criterion."),
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "Eligible clients supply benign calibration scores for pooled quantile construction.",
            ),
            reason=ValidationReasonText(
                "Pooled shared quantile is a shared-construction control for the natural-device population.",
            ),
            method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "Eligible clients supply benign calibration counts for sample-weighted shared construction.",
            ),
            reason=ValidationReasonText(
                "Sample-weighted shared threshold is a shared-construction control for natural devices.",
            ),
            method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText("Shared and local endpoints are available under one frozen detector."),
            reason=ValidationReasonText(
                "The predeclared fixed-lambda shrinkage curve is supported for the natural-device population.",
            ),
            method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "Eligible clients supply ordered benign calibration scores for finite-sample conformal ranks.",
            ),
            reason=ValidationReasonText(
                "Local conformal threshold is a supportive coverage diagnostic for the natural-device population.",
            ),
            method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "Eligible clients can publish benign-only summary statistics under the declared comparator.",
            ),
            reason=ValidationReasonText(
                "Federated benign-statistics is a threshold-variant comparator for the natural-device population.",
            ),
            method=FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "Eligible clients supply the exact benign calibration support used for local quantiles.",
            ),
            reason=ValidationReasonText(
                "Size-aware shrinkage uses the prospectively locked calibration-support rule.",
            ),
            method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        ),
    ),
)
