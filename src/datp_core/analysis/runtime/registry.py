"""Result registry — open registration of analysis result types for codec dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from attrs import define

from datp_core.analysis.enums import AnalysisResultKind
from datp_core.analysis.errors import (
    DuplicateResultKindError,
    DuplicateResultTypeError,
    ResultRegistryError,
    UnknownResultKindError,
    UnsupportedPayloadVersionError,
)

if TYPE_CHECKING:
    from datp_core.analysis.contracts import AnalysisResultContract


@define(frozen=True, slots=True)
class ResultKindEntry:
    """One registered result family."""

    result_kind: AnalysisResultKind
    result_type: type[AnalysisResultContract]
    payload_version: int


class AnalysisResultRegistry:
    """Typed registry mapping ``AnalysisResultKind`` to its result class."""

    def __init__(self) -> None:
        self._by_kind: dict[AnalysisResultKind, ResultKindEntry] = {}
        self._by_type: dict[type[Any], AnalysisResultKind] = {}

    def register(self, entry: ResultKindEntry) -> None:
        if entry.payload_version <= 0:
            raise UnsupportedPayloadVersionError(
                f"Payload version for '{entry.result_kind.value}' must be positive, got {entry.payload_version}"
            )
        if entry.result_kind in self._by_kind:
            existing = self._by_kind[entry.result_kind]
            raise DuplicateResultKindError(
                f"Duplicate result-kind registration: {entry.result_kind.value} "
                f"(already registered to {existing.result_type.__name__})"
            )
        if entry.result_type in self._by_type:
            existing_kind = self._by_type[entry.result_type]
            raise DuplicateResultTypeError(
                f"Duplicate result-type registration: {entry.result_type.__name__} "
                f"(already registered to kind '{existing_kind.value}')"
            )
        self._by_kind[entry.result_kind] = entry
        self._by_type[entry.result_type] = entry.result_kind

    def get(self, kind: AnalysisResultKind) -> ResultKindEntry:
        try:
            return self._by_kind[kind]
        except KeyError:
            raise UnknownResultKindError(f"No result type registered for kind: {kind.value}") from None

    def kind_for(self, result: object) -> AnalysisResultKind:
        target_type = type(result)
        try:
            return self._by_type[target_type]
        except KeyError:
            raise ResultRegistryError(
                f"Result type '{target_type.__name__}' is not registered in result registry"
            ) from None

    def type_for(self, kind: AnalysisResultKind) -> type[AnalysisResultContract]:
        return self.get(kind).result_type

    def register_result_class(self, cls: type[AnalysisResultContract]) -> None:
        """Register a result class that declares ``result_kind`` and ``payload_version``."""
        kind = getattr(cls, "result_kind", None)
        version = getattr(cls, "payload_version", None)
        if not isinstance(kind, AnalysisResultKind) or not isinstance(version, int):
            raise ResultRegistryError(
                f"Class '{cls.__name__}' does not declare valid result_kind and payload_version class variables"
            )
        self.register(ResultKindEntry(result_kind=kind, result_type=cls, payload_version=version))


# Singleton registry instance
RESULT_REGISTRY = AnalysisResultRegistry()
