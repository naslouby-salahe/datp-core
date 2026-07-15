from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from datp_core.domain.artifacts.lineage import PartitionIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.data.datasets import Regime
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.scores import ClientRoster


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
