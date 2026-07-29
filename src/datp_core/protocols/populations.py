"""Population capability declarations."""

from datp_core.datasets.ciciot2023.schema import CICIOT2023_AUDITED_FILE_CLIENT_COUNT
from datp_core.datasets.edge_iiotset.capabilities import EDGE_TEMPORAL_SENSOR_GROUPS
from datp_core.datasets.edge_iiotset.schema import EDGE_BENIGN_SENSOR_GROUPS
from datp_core.datasets.nbaiot.schema import NBAIOT_DEVICE_IDENTITIES
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind
from datp_core.domain.values import ClientCount, DirichletConcentration

from .models import PopulationDeclaration

DIRICHLET_CONCENTRATIONS = tuple(DirichletConcentration(value) for value in (0.1, 0.3, 0.5, 1, 10))
POPULATIONS = (
    PopulationDeclaration(
        id=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
        client_count=ClientCount(len(NBAIOT_DEVICE_IDENTITIES)),
    ),
    PopulationDeclaration(
        id=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
        client_count=ClientCount(20),
    ),
    PopulationDeclaration(
        id=PopulationId.CICIOT_FILE_CLIENTS,
        dataset=DatasetId.CICIOT2023,
        identity_kind=PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS,
        client_count=CICIOT2023_AUDITED_FILE_CLIENT_COUNT,
    ),
    PopulationDeclaration(
        id=PopulationId.EDGE_SENSOR_GROUPS,
        dataset=DatasetId.EDGE_IIOTSET,
        identity_kind=PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
        client_count=ClientCount(len(EDGE_BENIGN_SENSOR_GROUPS)),
    ),
    PopulationDeclaration(
        id=PopulationId.EDGE_TEMPORAL_GROUPS,
        dataset=DatasetId.EDGE_IIOTSET,
        identity_kind=PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
        client_count=ClientCount(len(EDGE_TEMPORAL_SENSOR_GROUPS)),
    ),
)
