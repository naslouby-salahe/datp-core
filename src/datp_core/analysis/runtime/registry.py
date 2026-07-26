"""Result registry — open registration of analysis result types for codec dispatch.

Replaces the manually maintained ``AnalysisResult`` union in ``result.py``.
Adding a new result family requires registration here, not editing a giant type
alias.
"""

from __future__ import annotations

from attrs import define

from datp_core.analysis.enums import AnalysisResultKind
from datp_core.analysis.errors import ResultDecodingError


@define(frozen=True, slots=True)
class ResultKindEntry:
    """One registered result family."""

    result_kind: AnalysisResultKind
    result_type: type
    payload_version: int


class ResultRegistry:
    """Typed registry mapping ``AnalysisResultKind`` to its result class.

    Each result module registers its type at import time.  The codec uses this
    registry to decode persisted payloads without inspecting a giant union.
    """

    def __init__(self) -> None:
        self._by_kind: dict[AnalysisResultKind, ResultKindEntry] = {}
        self._by_type: dict[type, AnalysisResultKind] = {}

    def register(self, entry: ResultKindEntry) -> None:
        if entry.result_kind in self._by_kind:
            existing = self._by_kind[entry.result_kind]
            raise ResultDecodingError(
                f"Duplicate result-kind registration: {entry.result_kind.value} "
                f"(already registered to {existing.result_type.__name__})"
            )
        self._by_kind[entry.result_kind] = entry
        self._by_type[entry.result_type] = entry.result_kind

    def get(self, kind: AnalysisResultKind) -> ResultKindEntry:
        try:
            return self._by_kind[kind]
        except KeyError:
            raise ResultDecodingError(f"No result type registered for kind: {kind.value}") from None

    def kind_for(self, result: object) -> AnalysisResultKind:
        try:
            return self._by_type[type(result)]
        except KeyError:
            raise ResultDecodingError(
                f"Result type '{type(result).__name__}' is not registered"
            ) from None


# Module-level singleton — the canonical analysis result registry.
RESULT_REGISTRY = ResultRegistry()
