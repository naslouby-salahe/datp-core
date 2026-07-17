from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Final

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, PartitionIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.data.datasets import Dataset, Regime
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster

N_BAIOT_NATURAL_DEVICE_COUNT: Final = 9


class ClientDefinitionStrategy(StrEnum):
    NATURAL_DEVICE = "natural_device"
    FILE_PSEUDO_CLIENT = "file_pseudo_client"
    DEVICE_CLIENT = "device_client"
    GROUP_CLIENT = "group_client"
    DIRICHLET_SYNTHETIC = "dirichlet_synthetic"


class DirichletAlphaSentinel(StrEnum):
    IID = "iid"


def _numeric_dirichlet_alpha(value: float | int | DirichletAlphaSentinel) -> float:
    if isinstance(value, bool):
        raise DomainValidationError(
            detail="Dirichlet alpha must be a finite positive number or the IID sentinel",
            value=repr(value),
            constraint="finite Dirichlet alpha > 0 or IID",
        )
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as error:
        raise DomainValidationError(
            detail="Dirichlet alpha must be a finite positive number or the IID sentinel",
            value=repr(value),
            constraint="finite Dirichlet alpha > 0 or IID",
        ) from error
    if not isfinite(numeric_value) or numeric_value <= 0:
        raise DomainValidationError(
            detail="Dirichlet alpha must be finite and strictly positive",
            value=str(numeric_value),
            constraint="finite Dirichlet alpha > 0",
        )
    return numeric_value


@dataclass(frozen=True, slots=True, kw_only=True)
class DirichletAlpha:
    value: float | DirichletAlphaSentinel

    def __post_init__(self) -> None:
        if self.value is DirichletAlphaSentinel.IID:
            return
        object.__setattr__(self, "value", _numeric_dirichlet_alpha(self.value))


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ClientPartitionSpec:
    strategy: ClientDefinitionStrategy
    regime: Regime


@dataclass(frozen=True, slots=True, kw_only=True)
class NaturalDevicePartitionSpec(ClientPartitionSpec):
    def __post_init__(self) -> None:
        if self.strategy is not ClientDefinitionStrategy.NATURAL_DEVICE:
            raise DomainValidationError(
                detail="natural-device partition must use the natural-device strategy",
                value=self.strategy.value,
                constraint="NATURAL_DEVICE strategy",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FilePseudoClientPartitionSpec(ClientPartitionSpec):
    def __post_init__(self) -> None:
        if self.strategy is not ClientDefinitionStrategy.FILE_PSEUDO_CLIENT:
            raise DomainValidationError(
                detail="file pseudo-client partition must use the file pseudo-client strategy",
                value=self.strategy.value,
                constraint="FILE_PSEUDO_CLIENT strategy",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DeviceClientPartitionSpec(ClientPartitionSpec):
    def __post_init__(self) -> None:
        if self.strategy is not ClientDefinitionStrategy.DEVICE_CLIENT:
            raise DomainValidationError(
                detail="device-client partition must use the device-client strategy",
                value=self.strategy.value,
                constraint="DEVICE_CLIENT strategy",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class GroupClientPartitionSpec(ClientPartitionSpec):
    def __post_init__(self) -> None:
        if self.strategy is not ClientDefinitionStrategy.GROUP_CLIENT:
            raise DomainValidationError(
                detail="group-client partition must use the group-client strategy",
                value=self.strategy.value,
                constraint="GROUP_CLIENT strategy",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DirichletPartitionSpec(ClientPartitionSpec):
    alpha: DirichletAlpha

    def __post_init__(self) -> None:
        if self.strategy is not ClientDefinitionStrategy.DIRICHLET_SYNTHETIC:
            raise DomainValidationError(
                detail="Dirichlet partition must use the Dirichlet synthetic strategy",
                value=self.strategy.value,
                constraint="DIRICHLET_SYNTHETIC strategy",
            )


type PartitionSpecification = (
    NaturalDevicePartitionSpec
    | FilePseudoClientPartitionSpec
    | DeviceClientPartitionSpec
    | GroupClientPartitionSpec
    | DirichletPartitionSpec
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientPartitionResult:
    partition_manifest: ArtifactRef
    client_roster: ClientRoster
    partition_identity: PartitionIdentity


def _validated_row_count(value: int) -> None:
    if isinstance(value, bool) or value < 1:
        raise DomainValidationError(
            detail="client row membership requires a positive row count",
            value=repr(value),
            constraint="row count >= 1",
        )


def _validated_row_order_checksum(value: str) -> None:
    if not value:
        raise DomainValidationError(
            detail="client row membership requires a non-empty row-order checksum",
            value=repr(value),
            constraint="non-empty row-order checksum",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientRowMembership:
    client_id: ClientId
    row_count: int
    row_order_checksum: str

    def __post_init__(self) -> None:
        _validated_row_count(self.row_count)
        _validated_row_order_checksum(self.row_order_checksum)


def _validated_membership_matches_roster(*, membership_ids: tuple[str, ...], roster: ClientRoster) -> None:
    if sorted(membership_ids) != sorted(client_id.value for client_id in roster.client_ids):
        raise DomainValidationError(
            detail="client partition manifest membership must exactly match the client roster",
            value=repr(membership_ids),
            constraint="membership client ids == roster client ids",
        )


def _validated_unique_membership_ids(membership_ids: tuple[str, ...]) -> None:
    if len(set(membership_ids)) != len(membership_ids):
        raise DomainValidationError(
            detail="client partition manifest membership client ids must be unique",
            value=repr(membership_ids),
            constraint="unique membership client ids",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientPartitionManifest:
    dataset: Dataset
    strategy: ClientDefinitionStrategy
    source_row_identity: DatasetSourceIdentity
    client_roster: ClientRoster
    client_row_memberships: tuple[ClientRowMembership, ...]

    def __post_init__(self) -> None:
        membership_ids = tuple(membership.client_id.value for membership in self.client_row_memberships)
        _validated_membership_matches_roster(membership_ids=membership_ids, roster=self.client_roster)
        _validated_unique_membership_ids(membership_ids)
