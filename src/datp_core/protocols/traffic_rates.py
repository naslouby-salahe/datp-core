"""Operational traffic-rate evidence declarations."""

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import PopulationId
from datp_core.domain.values.ratios import TrafficRatePerDay


class TrafficRateEvidence(StrictModel):
    population: PopulationId
    rate_per_day: TrafficRatePerDay
    source_locator: str

    @model_validator(mode="after")
    def validate_source_locator(self) -> "TrafficRateEvidence":
        if not self.source_locator.strip():
            raise ValueError("traffic-rate evidence requires a source locator")
        return self


TRAFFIC_RATE_EVIDENCE: tuple[TrafficRateEvidence, ...] = ()
