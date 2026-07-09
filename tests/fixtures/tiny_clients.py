"""Tiny deterministic client-identity fixture. Illustrative shape only, not real device data."""

from __future__ import annotations

from datp_core.domain.clients import ClientId, ClientIdentityType


def tiny_clients(n: int = 3) -> tuple[ClientId, ...]:
    return tuple(
        ClientId(value=f"fixture-client-{i}", identity_type=ClientIdentityType.PHYSICAL_DEVICE)
        for i in range(n)
    )
