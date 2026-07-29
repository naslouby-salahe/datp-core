"""Population capability declarations."""

from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind
from datp_core.domain.values import ClientCount, DirichletConcentration

from .models import PopulationDeclaration

DIRICHLET_CONCENTRATIONS = tuple(DirichletConcentration(value) for value in (0.1, 0.3, 0.5, 1, 10))
POPULATIONS = (
    PopulationDeclaration(
        id=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
        client_count=ClientCount(9),
        has_attack_assignment=True,
        has_chronology=False,
        has_family_taxonomy=True,
        confirmatory_eligible=True,
    ),
    PopulationDeclaration(
        id=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
        client_count=ClientCount(20),
        has_attack_assignment=True,
        has_chronology=False,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
    PopulationDeclaration(
        id=PopulationId.CICIOT_FILE_CLIENTS,
        dataset=DatasetId.CICIOT2023,
        identity_kind=PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS,
        client_count=ClientCount(63),
        has_attack_assignment=False,
        has_chronology=False,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
    PopulationDeclaration(
        id=PopulationId.EDGE_SENSOR_GROUPS,
        dataset=DatasetId.EDGE_IIOTSET,
        identity_kind=PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
        client_count=ClientCount(10),
        has_attack_assignment=False,
        has_chronology=False,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
    PopulationDeclaration(
        id=PopulationId.EDGE_TEMPORAL_GROUPS,
        dataset=DatasetId.EDGE_IIOTSET,
        identity_kind=PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
        client_count=ClientCount(9),
        has_attack_assignment=False,
        has_chronology=True,
        has_family_taxonomy=False,
        confirmatory_eligible=False,
    ),
)
