"""Population declarations owned by the scientific protocol layer."""

from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind
from datp_core.domain.values import ClientCount, DirichletConcentration

from .models import PopulationDeclaration

DIRICHLET_CONCENTRATIONS = tuple(DirichletConcentration(value) for value in (0.1, 0.3, 0.5, 1, 10))

NBAIOT_NATURAL_DEVICE_COUNT = ClientCount(9)
NBAIOT_DIRICHLET_CLIENT_COUNT = ClientCount(20)
CICIOT_FILE_CLIENT_COUNT = ClientCount(63)
EDGE_STATIC_SENSOR_GROUP_COUNT = ClientCount(10)
EDGE_TEMPORAL_SENSOR_GROUP_COUNT = ClientCount(9)

NBAIOT_NATURAL_DEVICES = PopulationDeclaration(
    id=PopulationId.NBAIOT_NATURAL_DEVICES,
    dataset=DatasetId.NBAIOT,
    identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
    client_count=NBAIOT_NATURAL_DEVICE_COUNT,
)
NBAIOT_DIRICHLET_CLIENTS = PopulationDeclaration(
    id=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
    dataset=DatasetId.NBAIOT,
    identity_kind=PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
    client_count=NBAIOT_DIRICHLET_CLIENT_COUNT,
)
CICIOT_FILE_CLIENTS = PopulationDeclaration(
    id=PopulationId.CICIOT_FILE_CLIENTS,
    dataset=DatasetId.CICIOT2023,
    identity_kind=PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS,
    client_count=CICIOT_FILE_CLIENT_COUNT,
)
EDGE_SENSOR_GROUPS = PopulationDeclaration(
    id=PopulationId.EDGE_SENSOR_GROUPS,
    dataset=DatasetId.EDGE_IIOTSET,
    identity_kind=PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
    client_count=EDGE_STATIC_SENSOR_GROUP_COUNT,
)
EDGE_TEMPORAL_GROUPS = PopulationDeclaration(
    id=PopulationId.EDGE_TEMPORAL_GROUPS,
    dataset=DatasetId.EDGE_IIOTSET,
    identity_kind=PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
    client_count=EDGE_TEMPORAL_SENSOR_GROUP_COUNT,
)

POPULATIONS = (
    NBAIOT_NATURAL_DEVICES,
    NBAIOT_DIRICHLET_CLIENTS,
    CICIOT_FILE_CLIENTS,
    EDGE_SENSOR_GROUPS,
    EDGE_TEMPORAL_GROUPS,
)
