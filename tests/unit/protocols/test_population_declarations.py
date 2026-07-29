from datp_core.domain.enums import PopulationId, PopulationIdentityKind
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS, POPULATIONS


def test_population_capabilities_and_dirichlet_grid() -> None:
    assert len(POPULATIONS) == 5
    assert tuple((population.id, population.client_count.value) for population in POPULATIONS) == (
        (PopulationId.NBAIOT_NATURAL_DEVICES, 9),
        (PopulationId.NBAIOT_DIRICHLET_CLIENTS, 20),
        (PopulationId.CICIOT_FILE_CLIENTS, 63),
        (PopulationId.EDGE_SENSOR_GROUPS, 10),
        (PopulationId.EDGE_TEMPORAL_GROUPS, 9),
    )
    assert not POPULATIONS[1].has_family_taxonomy
    assert tuple(item.value for item in DIRICHLET_CONCENTRATIONS) == (0.1, 0.3, 0.5, 1, 10)
    by_id = {population.id: population for population in POPULATIONS}
    assert by_id[PopulationId.NBAIOT_NATURAL_DEVICES].identity_kind is PopulationIdentityKind.PHYSICAL_DEVICES
    assert by_id[PopulationId.CICIOT_FILE_CLIENTS].identity_kind is PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS
    assert by_id[PopulationId.EDGE_SENSOR_GROUPS].identity_kind is PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS
    assert by_id[PopulationId.EDGE_TEMPORAL_GROUPS].identity_kind is PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS
    assert (
        by_id[PopulationId.NBAIOT_DIRICHLET_CLIENTS].identity_kind is PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS
    )
