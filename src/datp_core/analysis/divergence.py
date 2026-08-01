"""Heterogeneity analysis boundary: no divergence estimator without declared semantics."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue
from datp_core.populations.models import ClientIdentity


class DivergenceBlocker(StrEnum):
    COMMON_SUPPORT_UNRESOLVED = "common_support_unresolved"
    BINNING_UNRESOLVED = "binning_unresolved"
    DENSITY_UNRESOLVED = "density_unresolved"
    SMOOTHING_UNRESOLVED = "smoothing_unresolved"
    ZERO_MASS_UNRESOLVED = "zero_mass_unresolved"
    AGGREGATION_UNRESOLVED = "aggregation_unresolved"


@dataclass(frozen=True, slots=True)
class DivergenceResult:
    evidence_role: EvidenceRole
    clients: tuple[ClientIdentity, ...]
    pairwise_values: tuple[MetricValue, ...]
    aggregate: MetricValue | None
    availability: AvailabilityStatus
    blocker: DivergenceBlocker | None
    reason: str

    def __post_init__(self) -> None:
        if self.availability is AvailabilityStatus.AVAILABLE:
            if self.blocker is not None or not self.pairwise_values or self.aggregate is None or self.reason:
                raise ValueError("available divergence requires values, aggregate, and no blocker")
        elif self.blocker is None or self.pairwise_values or self.aggregate is not None or not self.reason:
            raise ValueError("blocked divergence must preserve its explicit unresolved construction")


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...], blocker: DivergenceBlocker
) -> DivergenceResult:
    """Return the required typed blocker instead of selecting histogram semantics ad hoc."""
    if len(clients) < 2:
        raise ValueError("divergence analysis requires at least two clients")
    return DivergenceResult(
        EvidenceRole.MECHANISM,
        tuple(sorted(clients, key=lambda item: item.client_id)),
        (),
        None,
        AvailabilityStatus.UNAVAILABLE,
        blocker,
        f"Jensen-Shannon divergence is blocked: {blocker.value}",
    )
