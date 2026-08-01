"""Validation records for operational decision-rate evidence."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import PopulationId, TrafficRateEvidenceType
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import TrafficRatePerDay


class TrafficRateUnit(StrEnum):
    BENIGN_DECISIONS_PER_CLIENT_PER_DAY = "benign_decisions_per_client_per_day"


class TrafficRateGranularity(StrEnum):
    PER_CLIENT = "per_client"
    POPULATION = "population"


@dataclass(frozen=True, slots=True)
class ValidatedTrafficRateEvidence:
    """Operational rate evidence with explicit applicability and provenance."""

    evidence_kind: TrafficRateEvidenceType
    population: PopulationId
    rate_per_day: TrafficRatePerDay
    source_locator: str
    provenance: str
    unit: TrafficRateUnit
    granularity: TrafficRateGranularity
    applicable_to_each_client: bool

    def __post_init__(self) -> None:
        if self.evidence_kind is TrafficRateEvidenceType.UNAVAILABLE:
            raise ScientificContractError("unavailable traffic-rate evidence cannot support operational calculation")
        if not self.source_locator.strip() or not self.provenance.strip():
            raise ScientificContractError("traffic-rate evidence requires source and provenance")
        if self.granularity is TrafficRateGranularity.PER_CLIENT and not self.applicable_to_each_client:
            raise ScientificContractError("per-client traffic-rate evidence must be applicable to each client")


def validate_traffic_rate_evidence(evidence: ValidatedTrafficRateEvidence) -> ValidatedTrafficRateEvidence:
    """Provide an explicit validation boundary for only supported evidence kinds."""
    if evidence.evidence_kind not in {
        TrafficRateEvidenceType.MEASURED,
        TrafficRateEvidenceType.DATASET_DERIVED,
        TrafficRateEvidenceType.EXTERNALLY_CITED,
    }:
        raise ScientificContractError("traffic-rate evidence kind is not operationally valid")
    return evidence
