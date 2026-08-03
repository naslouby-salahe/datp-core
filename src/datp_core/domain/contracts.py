"""Shared domain contracts."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Immutable, strict document model used at every serialized-domain boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


@dataclass(frozen=True, slots=True)
class ClientOwned[ClientT, ValueT]:
    """One value with exactly one authoritative client owner."""

    client: ClientT
    value: ValueT


@dataclass(frozen=True, slots=True)
class ClientCollection[ClientT, ValueT]:
    """A non-empty, uniquely owned client collection."""

    items: tuple[ClientOwned[ClientT, ValueT], ...]

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("client collection cannot be empty")
        clients = tuple(item.client for item in self.items)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("client collection cannot contain duplicate owners")

    def require(self, client: ClientT) -> ValueT:
        matches = tuple(item.value for item in self.items if item.client == client)
        if len(matches) != 1:
            raise KeyError(f"expected exactly one value for client {client}")
        return matches[0]

    def clients(self) -> tuple[ClientT, ...]:
        return tuple(item.client for item in self.items)

    def values(self) -> tuple[ValueT, ...]:
        return tuple(item.value for item in self.items)
