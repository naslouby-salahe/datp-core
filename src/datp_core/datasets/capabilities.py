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
    conditional_metrics: tuple[MetricId, ...]
    unavailable_metrics: tuple[MetricId, ...]

    def __post_init__(self) -> None:
        groups = (self.available_metrics, self.conditional_metrics, self.unavailable_metrics)
        declared = tuple(metric for group in groups for metric in group)
        if not declared or len(declared) != len(frozenset(declared)):
            raise ValueError("metric capabilities must declare non-overlapping metrics")
        statuses = frozenset(
            status
            for metrics, status in (
                (self.available_metrics, CapabilityStatus.SUPPORTED),
                (self.conditional_metrics, CapabilityStatus.CONDITIONAL),
                (self.unavailable_metrics, CapabilityStatus.UNAVAILABLE),
            )
            if metrics
        )
        aggregate = (
            CapabilityStatus.SUPPORTED if statuses == {CapabilityStatus.SUPPORTED} else CapabilityStatus.UNAVAILABLE
        )
        if len(statuses) > 1 or CapabilityStatus.CONDITIONAL in statuses:
            aggregate = CapabilityStatus.CONDITIONAL
        if self.status is not aggregate:
            raise ValueError("metric capability status must match its explicit metric declarations")

    def status_for(self, metric: MetricId) -> CapabilityStatus:
        if metric in self.available_metrics:
            return CapabilityStatus.SUPPORTED
        if metric in self.conditional_metrics:
            return CapabilityStatus.CONDITIONAL
        if metric in self.unavailable_metrics:
            return CapabilityStatus.UNAVAILABLE
        return CapabilityStatus.UNAVAILABLE


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
        if not self.valid_populations:
            raise ValueError("dataset capabilities require valid populations")
        if len(self.valid_populations) != len(frozenset(self.valid_populations)):
            raise ValueError("dataset capability populations must be unique")
        methods = tuple(capability.method for capability in self.threshold_methods)
        if len(methods) != len(frozenset(methods)):
            raise ValueError("threshold method capabilities must be unique")
