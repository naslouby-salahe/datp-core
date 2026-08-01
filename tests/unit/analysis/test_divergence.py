from datp_core.analysis.divergence import DivergenceBlocker, blocked_jensen_shannon_divergence
from datp_core.domain.enums import AvailabilityStatus, PopulationId, PopulationIdentityKind
from datp_core.populations.models import ClientIdentity


def test_unresolved_jsd_semantics_produce_a_typed_blocker_without_histogram_estimation() -> None:
    clients = (
        ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, "client_a", PopulationIdentityKind.PHYSICAL_DEVICES),
        ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, "client_b", PopulationIdentityKind.PHYSICAL_DEVICES),
    )

    result = blocked_jensen_shannon_divergence(clients, DivergenceBlocker.BINNING_UNRESOLVED)

    assert result.availability is AvailabilityStatus.UNAVAILABLE
    assert result.blocker is DivergenceBlocker.BINNING_UNRESOLVED
    assert result.pairwise_values == ()
    assert result.aggregate is None
