"""Analysis handler registry keyed by AnalysisKind.

Each analysis capability registers its handler by kind. The registry is assembled
in the composition root and injected into the pipeline stage handler.
"""

from __future__ import annotations

from collections.abc import Callable

from datp_core.analysis.contracts import AnalysisResult, PairedAnalysisCell
from datp_core.analysis.errors import DuplicateAnalysisRegistrationError, UnsupportedAnalysisRecordError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.experiments.catalogue.analyses import AnalysisKind, AnalysisRecord


class AnalysisHandlerRegistry:
    """Maps AnalysisKind to analysis handler implementations.

    Assembled in the composition root. Each handler receives the analysis
    specification record, execution context, and optional sweep cell.
    """

    def __init__(self) -> None:
        self._handlers: dict[AnalysisKind, Callable[..., tuple[AnalysisResult, ...]]] = {}

    def register(
        self,
        kind: AnalysisKind,
        handler: Callable[..., tuple[AnalysisResult, ...]],
    ) -> None:
        if kind in self._handlers:
            raise DuplicateAnalysisRegistrationError(
                f"Analysis handler already registered for kind: {kind.value}"
            )
        self._handlers[kind] = handler

    def dispatch(
        self,
        specification: AnalysisRecord,
        context: AnalysisExecutionContext,
        cell: PairedAnalysisCell | None = None,
    ) -> tuple[AnalysisResult, ...]:
        kind = AnalysisKind(specification.kind)
        handler = self._handlers.get(kind)
        if handler is None:
            raise UnsupportedAnalysisRecordError(
                f"No handler registered for analysis kind: {kind.value}"
            )
        return handler(specification, context, cell)
