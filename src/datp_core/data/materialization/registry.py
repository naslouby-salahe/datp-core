"""Immutable dataset-materializer registry."""

from __future__ import annotations

from datp_core.data.contracts.enums import AdapterKind, DataFailureCode
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import DatasetMaterializer


class DatasetAdapterRegistry:
    __slots__ = ("_adapters",)

    def __init__(self, adapters: tuple[DatasetMaterializer, ...]) -> None:
        kinds = tuple(adapter.adapter_kind for adapter in adapters)
        if len(kinds) != len(frozenset(kinds)):
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "dataset materializer registry contains duplicate adapter kinds",
                source_path=None,
                source_row_index=None,
            )
        self._adapters = tuple(sorted(adapters, key=lambda adapter: adapter.adapter_kind.value))

    def get(self, kind: AdapterKind) -> DatasetMaterializer:
        for adapter in self._adapters:
            if adapter.adapter_kind is kind:
                return adapter
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            f"no materializer registered for adapter '{kind.value}'",
            source_path=None,
            source_row_index=None,
        )

    @property
    def registered_kinds(self) -> tuple[AdapterKind, ...]:
        return tuple(adapter.adapter_kind for adapter in self._adapters)
