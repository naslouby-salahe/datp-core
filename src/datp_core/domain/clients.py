"""Client identity types and typed client identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ClientIdentityType(StrEnum):
    PHYSICAL_DEVICE = "physical_device"
    FILE_LEVEL_PSEUDO_CLIENT = "file_level_pseudo_client"
    DEVICE_GROUP = "device_group"
    SYNTHETIC_DIRICHLET_CLIENT = "synthetic_dirichlet_client"


@dataclass(frozen=True)
class ClientId:
    value: str
    identity_type: ClientIdentityType

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ClientId.value must not be empty")
