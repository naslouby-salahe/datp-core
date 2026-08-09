from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import PopulationId, TrafficRateEvidenceType
from datp_core.core.numeric import TrafficRatePerDay


class TrafficRateUnit(StrEnum):
    BENIGN_DECISIONS_PER_CLIENT_PER_DAY = "benign_decisions_per_client_per_day"


class TrafficRateGranularity(StrEnum):
    PER_CLIENT = "per_client"
    POPULATION = "population"


_VALID_EVIDENCE_KINDS = frozenset(
    {
        TrafficRateEvidenceType.MEASURED,
        TrafficRateEvidenceType.DATASET_DERIVED,
        TrafficRateEvidenceType.EXTERNALLY_CITED,
    }
)


@dataclass(frozen=True, slots=True)
class ValidatedTrafficRateEvidence:
    evidence_kind: TrafficRateEvidenceType
    population: PopulationId
    rate_per_day: TrafficRatePerDay
    source_locator: str #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    provenance: str#TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    unit: TrafficRateUnit
    granularity: TrafficRateGranularity
    applicable_to_each_client: bool

    def __post_init__(self) -> None:
        if self.evidence_kind is TrafficRateEvidenceType.UNAVAILABLE:
            raise ScientificContractError("unavailable traffic-rate evidence cannot support operational calculation")
        if not self.source_locator or self.source_locator.isspace() or not self.provenance or self.provenance.isspace():
            raise ScientificContractError("traffic-rate evidence requires source and provenance")
        if self.granularity is TrafficRateGranularity.PER_CLIENT and not self.applicable_to_each_client:
            raise ScientificContractError("per-client traffic-rate evidence must be applicable to each client")


def validate_traffic_rate_evidence(evidence: ValidatedTrafficRateEvidence) -> ValidatedTrafficRateEvidence:
    if evidence.evidence_kind not in _VALID_EVIDENCE_KINDS:
        raise ScientificContractError("traffic-rate evidence kind is not operationally valid")
    return evidence


class TrafficRateLocatorScheme(StrEnum):
    """Fixed shape of a traffic-rate evidence reference (not free-form prose)."""

    DATASET_PATH = "dataset_path"
    EXTERNAL_URL = "external_url"
    EXTERNAL_DOI = "external_doi"
    EXTERNAL_CITATION = "external_citation"


class TrafficRateSourceLocator(StrictModel):
    """A structured reference to one traffic-rate evidence source."""

    scheme: TrafficRateLocatorScheme
    reference: str#TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity

    @model_validator(mode="after")
    def validate_reference(self) -> "TrafficRateSourceLocator":
        if not self.reference.strip():
            raise ValueError("traffic-rate source locator requires a non-empty reference")
        return self

    def as_text(self) -> str:
        return f"{self.scheme.value}:{self.reference}"


class TrafficRateEvidence(StrictModel):
    population: PopulationId
    rate_per_day: TrafficRatePerDay
    evidence_kind: TrafficRateEvidenceType
    source_locator: TrafficRateSourceLocator
    provenance: str#TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    unit: TrafficRateUnit
    granularity: TrafficRateGranularity
    applicable_to_each_client: bool

    @model_validator(mode="after")
    def validate_evidence(self) -> "TrafficRateEvidence":
        if self.evidence_kind is TrafficRateEvidenceType.UNAVAILABLE:
            raise ValueError("unavailable traffic-rate evidence cannot be declared")
        if not self.provenance.strip():
            raise ValueError("traffic-rate evidence requires provenance")
        if self.granularity is TrafficRateGranularity.PER_CLIENT and not self.applicable_to_each_client:
            raise ValueError("per-client traffic-rate evidence must be applicable to each client")
        return self

    def to_validated(self) -> ValidatedTrafficRateEvidence:
        return validate_traffic_rate_evidence(
            ValidatedTrafficRateEvidence(
                evidence_kind=self.evidence_kind,
                population=self.population,
                rate_per_day=self.rate_per_day,
                source_locator=self.source_locator.as_text(),
                provenance=self.provenance,
                unit=self.unit,
                granularity=self.granularity,
                applicable_to_each_client=self.applicable_to_each_client,
            )
        )


TRAFFIC_RATE_EVIDENCE: tuple[TrafficRateEvidence, ...] = ()


def traffic_rate_evidence_for_population(population: PopulationId) -> ValidatedTrafficRateEvidence | None:
    for declared in TRAFFIC_RATE_EVIDENCE:
        if declared.population is population:
            return declared.to_validated()
    return None
