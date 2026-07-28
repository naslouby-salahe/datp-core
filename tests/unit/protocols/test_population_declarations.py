from datp_core.domain.enums import PopulationId
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS, POPULATIONS


def test_population_capabilities_and_dirichlet_grid() -> None:
    assert len(POPULATIONS) == 5
    assert POPULATIONS[0].id is PopulationId.NBAIOT_NATURAL_DEVICES
    assert tuple(item.value for item in DIRICHLET_CONCENTRATIONS) == (0.1, 0.3, 0.5, 1, 10)
