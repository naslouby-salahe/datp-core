"""Population capability declarations."""

from datp_core.domain.enums import DatasetId, PopulationId
from datp_core.domain.values import ClientCount, DirichletConcentration

from .models import PopulationDeclaration

DIRICHLET_CONCENTRATIONS = tuple(DirichletConcentration(value) for value in (0.1, 0.3, 0.5, 1, 10))
POPULATIONS = (
    PopulationDeclaration(
        id=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        client_count=ClientCount(9),
        has_attack_assignment=True,
        has_chronology=False,
        has_family_taxonomy=True,
        confirmatory_eligible=True,
    ),
    PopulationDeclaration(
        id=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        dataset=DatasetId.NBAIOT,
        client_count=ClientCount(20),
        has_attack_assignment=True,
        has_chronology=False,
        has_family_taxonomy=True,
        confirmatory_eligible=False,
    ),
    PopulationDeclaration(
        id=PopulationId.CICIOT_FILE_CLIENTS,
        dataset=DatasetId.CICIOT2023,
        client_count=ClientCount(1),
        has_attack_assignment=False,
        has_chronology=False,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
    PopulationDeclaration(
        id=PopulationId.EDGE_SENSOR_GROUPS,
        dataset=DatasetId.EDGE_IIOTSET,
        client_count=ClientCount(1),
        has_attack_assignment=False,
        has_chronology=False,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
    PopulationDeclaration(
        id=PopulationId.EDGE_TEMPORAL_GROUPS,
        dataset=DatasetId.EDGE_IIOTSET,
        client_count=ClientCount(1),
        has_attack_assignment=False,
        has_chronology=True,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
)
