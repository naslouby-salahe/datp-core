"""Population declarations owned by the scientific protocol layer."""

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import DatasetId, PopulationId, PopulationIdentityKind, SplitProtocolId
from datp_core.domain.values.counts import ClientCount
from datp_core.domain.values.ratios import DirichletConcentration


class PopulationDeclaration(StrictModel):
    id: PopulationId
    dataset: DatasetId
    identity_kind: PopulationIdentityKind
    client_count: ClientCount

    @model_validator(mode="after")
    def validate_identity_kind(self) -> "PopulationDeclaration":
        match self.identity_kind:
            case PopulationIdentityKind.PHYSICAL_DEVICES:
                if self.dataset is not DatasetId.NBAIOT:
                    raise ValueError("physical-device populations must be confirmatory N-BaIoT devices")
            case PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS:
                if self.dataset is not DatasetId.CICIOT2023:
                    raise ValueError("file-defined pseudo-clients cannot be confirmatory physical devices")
            case PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS:
                if self.dataset is not DatasetId.EDGE_IIOTSET:
                    raise ValueError("source-defined sensor groups are not physical attack-assigned devices")
            case PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS:
                if self.dataset is not DatasetId.NBAIOT:
                    raise ValueError("synthetic Dirichlet clients are not confirmatory physical devices")
            case PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS:
                if self.dataset is not DatasetId.EDGE_IIOTSET:
                    raise ValueError("verified temporal groups require Edge chronology")
        return self

    @property
    def is_confirmatory_population(self) -> bool:
        return self.identity_kind is PopulationIdentityKind.PHYSICAL_DEVICES

    @property
    def requires_family_taxonomy(self) -> bool:
        return self.is_confirmatory_population

    @property
    def requires_verified_chronology(self) -> bool:
        return self.identity_kind is PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS

    @property
    def requires_client_attack_assignment(self) -> bool:
        return self.identity_kind in {
            PopulationIdentityKind.PHYSICAL_DEVICES,
            PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
        }


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


def split_protocol_for_population(population: PopulationId) -> SplitProtocolId:
    """Resolve the single declared split protocol for one population identity."""
    match population:
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            return SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        case PopulationId.EDGE_SENSOR_GROUPS:
            return SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
        case (
            PopulationId.NBAIOT_NATURAL_DEVICES
            | PopulationId.NBAIOT_DIRICHLET_CLIENTS
            | PopulationId.CICIOT_FILE_CLIENTS
        ):
            return SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
