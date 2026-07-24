"""Immutable adapter registry."""

from __future__ import annotations

from datp_core.data.contracts.enums import AdapterKind
from datp_core.data.materialization.ports import DatasetMaterializer


class DatasetAdapterRegistry:
    def __init__(self, adapters: dict[AdapterKind, DatasetMaterializer]) -> None:
        self._adapters: dict[AdapterKind, DatasetMaterializer] = dict(adapters)

    def get(self, kind: AdapterKind) -> DatasetMaterializer:
        try:
            return self._adapters[kind]
        except KeyError:
            raise KeyError(
                f"No dataset materializer registered for adapter kind '{kind.value}'. "
                f"Registered kinds: {[k.value for k in self._adapters]}"
            ) from None

    @property
    def registered_kinds(self) -> tuple[AdapterKind, ...]:
        return tuple(sorted(self._adapters.keys(), key=lambda k: k.value))
