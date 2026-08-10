from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    PopulationId,
    TrafficRateEvidenceType,
    TrafficRateLocatorText,
    TrafficRateProvenanceText,
    TrafficRateReference,
)
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
    source_locator: TrafficRateLocatorText
    provenance: TrafficRateProvenanceText
    unit: TrafficRateUnit
    granularity: TrafficRateGranularity
    applicable_to_each_client: bool

    def __post_init__(self) -> None:
        if self.evidence_kind is TrafficRateEvidenceType.UNAVAILABLE:
            raise ScientificContractError(
                ErrorMessage("unavailable traffic-rate evidence cannot support operational calculation")
            )
        object.__setattr__(self, "source_locator", TrafficRateLocatorText(self.source_locator))
        object.__setattr__(self, "provenance", TrafficRateProvenanceText(self.provenance))
        if self.granularity is TrafficRateGranularity.PER_CLIENT and not self.applicable_to_each_client:
            raise ScientificContractError(
                ErrorMessage("per-client traffic-rate evidence must be applicable to each client")
            )


def validate_traffic_rate_evidence(evidence: ValidatedTrafficRateEvidence) -> ValidatedTrafficRateEvidence:
    if evidence.evidence_kind not in _VALID_EVIDENCE_KINDS:
        raise ScientificContractError(ErrorMessage("traffic-rate evidence kind is not operationally valid"))
    return evidence


class TrafficRateLocatorScheme(StrEnum):
    DATASET_PATH = "dataset_path"
    EXTERNAL_URL = "external_url"
    EXTERNAL_DOI = "external_doi"
    EXTERNAL_CITATION = "external_citation"


class TrafficRateSourceLocator(StrictModel):
    scheme: TrafficRateLocatorScheme
    reference: TrafficRateReference

    @model_validator(mode="after")
    def validate_reference(self) -> "TrafficRateSourceLocator":
        if not self.reference.strip():
            raise ValueError("traffic-rate source locator requires a non-empty reference")
        return self

    def as_text(self) -> TrafficRateLocatorText:
        return TrafficRateLocatorText(f"{self.scheme.value}:{self.reference}")


class TrafficRateEvidence(StrictModel):
    population: PopulationId
    rate_per_day: TrafficRatePerDay
    evidence_kind: TrafficRateEvidenceType
    source_locator: TrafficRateSourceLocator
    provenance: TrafficRateProvenanceText
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
