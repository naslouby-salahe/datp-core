"""Dataset adapter registry mapping AdapterKind to materializer implementations.

Registered adapters implement the DatasetMaterializer port from application/ports.py.
The composition root wires concrete adapters into the registry.
"""

from __future__ import annotations

from attrs import define

from datp_core.application.ports import DatasetMaterializer
from datp_core.domain.datasets import AdapterKind


@define(frozen=True, slots=True, kw_only=True)
class DatasetAdapterRegistry:
    """Immutable registry of dataset materializers indexed by AdapterKind."""

    adapters: dict[AdapterKind, DatasetMaterializer]

    def get(self, kind: AdapterKind) -> DatasetMaterializer:
        """Return the adapter registered for the given AdapterKind.

        Raises KeyError if no adapter is registered (missing-adapter error).
        """
        try:
            return self.adapters[kind]
        except KeyError:
            raise KeyError(
                f"No dataset materializer registered for adapter kind '{kind.value}'. "
                f"Registered kinds: {[k.value for k in self.adapters]}"
            ) from None

    @property
    def registered_kinds(self) -> tuple[AdapterKind, ...]:
        return tuple(self.adapters.keys())
