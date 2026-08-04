"""Declared Jensen-Shannon divergence boundary evidence."""

from enum import StrEnum
from typing import ClassVar

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, PairedObservationCount
from datp_core.populations.models import ClientIdentity

MINIMUM_DIVERGENCE_CLIENTS = PairedObservationCount(2)


class DivergenceBlocker(StrEnum):
    COMMON_SUPPORT_UNRESOLVED = "common_support_unresolved"
    BINNING_UNRESOLVED = "binning_unresolved"
    DENSITY_UNRESOLVED = "density_unresolved"
    SMOOTHING_UNRESOLVED = "smoothing_unresolved"
    ZERO_MASS_UNRESOLVED = "zero_mass_unresolved"
    AGGREGATION_UNRESOLVED = "aggregation_unresolved"

    @property
    def reason(self) -> str:
        return f"Jensen-Shannon divergence is blocked: {self.value}"


class DivergenceResult(StrictModel):
    clients: tuple[ClientIdentity, ...]
    pairwise_values: tuple[MetricValue, ...]
    aggregate: MetricValue | None
    blocker: DivergenceBlocker | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "DivergenceResult":
        if len(self.clients) < MINIMUM_DIVERGENCE_CLIENTS.value:
            raise ValueError("divergence analysis requires at least two clients")
        if len(set(self.clients)) != len(self.clients):
            raise ValueError("divergence analysis requires unique clients")
        available = self.blocker is None
        if available and (not self.pairwise_values or self.aggregate is None):
            raise ValueError(
                "available divergence requires pairwise values and an aggregate"
            )
        if not available and (self.pairwise_values or self.aggregate is not None):
            raise ValueError("blocked divergence cannot contain calculated values")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return (
            AvailabilityStatus.AVAILABLE
            if self.blocker is None
            else AvailabilityStatus.UNAVAILABLE
        )

    @property
    def reason(self) -> str | None:
        return None if self.blocker is None else self.blocker.reason


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...],
    blocker: DivergenceBlocker,
) -> DivergenceResult:
    return DivergenceResult(
        clients=tuple(sorted(clients)),
        pairwise_values=(),
        aggregate=None,
        blocker=blocker,
    )
