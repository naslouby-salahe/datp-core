from datp_core.core.identifiers import (
    EvidenceRole,
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

CICIOT2023_CAPABILITIES = DatasetCapabilities(
    physical_clients=PhysicalClientCapability(
        CapabilityStatus.UNAVAILABLE,
        ValidationReasonText("Merged CSVs preserve source-file identity but no physical-device identifier."),
        ValidationReasonText("The original topology cannot be reconstructed from the processed artifact."),
        (),
    ),
    family_taxonomy=FamilyTaxonomyCapability(
        CapabilityStatus.UNAVAILABLE,
        ValidationReasonText("No physical-device identities survive in the merged files."),
        ValidationReasonText("A device-family taxonomy cannot be derived from filenames or source-paper counts."),
        (),
    ),
    chronology=ChronologyCapability(
        CapabilityStatus.UNAVAILABLE,
        ValidationReasonText("The 40-column merged schema has no audited capture-time field."),
        ValidationReasonText("Merged-file ordering is not chronology evidence."),
        (),
    ),
    attack_assignment=AttackAssignmentCapability(
        CapabilityStatus.UNAVAILABLE,
        ValidationReasonText("The Label field supplies row-level attack labels only."),
        ValidationReasonText("Rows cannot be assigned to the original physical devices."),
        True,
        False,
    ),
    metrics=MetricCapability(
        CapabilityStatus.CONDITIONAL,
        ValidationReasonText("The full merged-file audit found nine null labels and 991 infinite Rate values."),
        ValidationReasonText(
            "Model inputs require the declared exclusion-only gate; raw canonical rows remain lossless and unmodified."
        ),
        (),
        tuple(MetricId),
        (),
    ),
    temporal=TemporalCapability(
        CapabilityStatus.UNAVAILABLE,
        ValidationReasonText("No source timestamp field is retained in merged files."),
        ValidationReasonText("Temporal experiments are prohibited."),
        False,
    ),
    external_validation=ExternalValidationCapability(
        CapabilityStatus.SUPPORTED,
        ValidationReasonText("The scientific source assigns CICIoT2023 a file-defined applicability-boundary role."),
        ValidationReasonText(
            "The approved outcome-blind eligibility gate must run before file-defined population construction."
        ),
        (EvidenceRole.APPLICABILITY_BOUNDARY,),
    ),
    valid_populations=(PopulationId.CICIOT_FILE_CLIENTS,),
    threshold_methods=(
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "File-defined pseudo-clients retain benign rows after the declared eligibility gate."
            ),
            reason=ValidationReasonText("The shared threshold remains an applicability-boundary comparison only."),
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.SUPPORTED,
            evidence=ValidationReasonText(
                "File-defined pseudo-clients retain benign rows after the declared eligibility gate."
            ),
            reason=ValidationReasonText("The local threshold remains an applicability-boundary comparison only."),
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        ThresholdMethodCapability(
            status=CapabilityStatus.CONDITIONAL,
            evidence=ValidationReasonText("Taxonomy-free clustering may use benign reconstruction-error summaries."),
            reason=ValidationReasonText(
                "Execution requires a separately declared, outcome-blind cluster-feasibility "
                "criterion after eligibility."
            ),
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        ),
    ),
)
