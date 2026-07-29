"""Evidence-backed dataset capability declarations."""

from dataclasses import dataclass

from datp_core.domain.enums import (
    CapabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)


@dataclass(frozen=True, slots=True)
class PhysicalClientCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    identities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FamilyTaxonomyCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    families: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChronologyCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    temporal_group_identities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AttackAssignmentCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    row_level_labels_available: bool
    client_level_assignment_available: bool


@dataclass(frozen=True, slots=True)
class MetricCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    available_metrics: tuple[MetricId, ...]
    unavailable_metrics: tuple[MetricId, ...]


@dataclass(frozen=True, slots=True)
class TemporalCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    supports_one_shot_recalibration: bool


@dataclass(frozen=True, slots=True)
class ExternalValidationCapability:
    status: CapabilityStatus
    evidence: str
    reason: str
    roles: tuple[EvidenceRole, ...]


@dataclass(frozen=True, slots=True)
class ThresholdMethodCapability:
    method: FederatedThresholdMethod
    status: CapabilityStatus
    evidence: str
    reason: str


@dataclass(frozen=True, slots=True)
class DatasetCapabilities:
    physical_clients: PhysicalClientCapability
    family_taxonomy: FamilyTaxonomyCapability
    chronology: ChronologyCapability
    attack_assignment: AttackAssignmentCapability
    metrics: MetricCapability
    temporal: TemporalCapability
    external_validation: ExternalValidationCapability
    valid_populations: tuple[PopulationId, ...]
    threshold_methods: tuple[ThresholdMethodCapability, ...]

    def __post_init__(self) -> None:
        methods = tuple(capability.method for capability in self.threshold_methods)
        if len(methods) != len(frozenset(methods)):
            raise ValueError("threshold method capabilities must be unique")
