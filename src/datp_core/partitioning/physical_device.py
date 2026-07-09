"""Natural physical-device client mapping for Regime A."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.clients import ClientId, ClientIdentityType


class PhysicalDeviceMappingError(ValueError):
    """Raised when physical-device identities cannot define Regime A clients."""


@dataclass(frozen=True)
class PhysicalDeviceClientMap:
    clients: tuple[ClientId, ...]
    expected_client_count: int

    def __post_init__(self) -> None:
        identifiers = tuple(client.value for client in self.clients)
        if not identifiers:
            raise PhysicalDeviceMappingError("Regime A requires at least one physical-device client")
        if len(set(identifiers)) != len(identifiers):
            raise PhysicalDeviceMappingError("Regime A physical-device client IDs must be unique")
        if any(client.identity_type is not ClientIdentityType.PHYSICAL_DEVICE for client in self.clients):
            raise PhysicalDeviceMappingError("Regime A accepts physical-device identities only")
        if len(self.clients) != self.expected_client_count:
            raise PhysicalDeviceMappingError(f"Regime A requires {self.expected_client_count} physical-device clients")

    @property
    def client_ids(self) -> tuple[str, ...]:
        return tuple(client.value for client in self.clients)


def build_physical_device_client_map(
    device_ids: tuple[str, ...], *, expected_client_count: int
) -> PhysicalDeviceClientMap:
    if not device_ids:
        raise PhysicalDeviceMappingError("physical-device metadata is required for Regime A")
    return PhysicalDeviceClientMap(
        clients=tuple(
            ClientId(value=device_id, identity_type=ClientIdentityType.PHYSICAL_DEVICE)
            for device_id in sorted(device_ids)
        ),
        expected_client_count=expected_client_count,
    )
