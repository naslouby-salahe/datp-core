"""Typed analysis dispatch via singledispatch registry.

Each analysis capability registers its own implementation by record type.
Adding a capability does not require editing a central conditional chain.
"""

from __future__ import annotations

from functools import singledispatch
from typing import TYPE_CHECKING

from attrs import define

from datp_core.analysis.errors import UnsupportedAnalysisError
from datp_core.analysis.runtime.context import AnalysisExecutionContext

if TYPE_CHECKING:
    from datp_core.experiments import AnalysisRecord


@singledispatch
def run_analysis(
    specification: object,
    context: AnalysisExecutionContext,
    cell: object | None = None,
) -> tuple:
    """Dispatch an analysis specification to its registered implementation.

    Each capability module registers its own handler via
    ``@run_analysis.register`` keyed on the analysis record type.
    """
    raise UnsupportedAnalysisError(
        f"No implementation registered for analysis type: {type(specification).__name__}"
    )


@define(frozen=True, slots=True)
class AnalysisRunner:
    """Resolves and executes the correct analysis implementation for each analysis record type."""

    context: AnalysisExecutionContext

    def run(
        self,
        specification: AnalysisRecord,
        *,
        cell: object | None = None,
    ) -> tuple:
        return run_analysis(specification, self.context, cell)
