"""Typed analysis dispatch via singledispatch registry.

Each analysis capability registers its own implementation by record type.
"""

from __future__ import annotations

from functools import singledispatch
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from datp_core.analysis.contracts import AnalysisResult, PairedAnalysisCell
from datp_core.analysis.errors import UnsupportedAnalysisRecordError
from datp_core.analysis.runtime.context import AnalysisExecutionContext

if TYPE_CHECKING:
    from datp_core.experiments import AnalysisRecord

_bootstrapped = False


@singledispatch
def run_analysis(
    specification: object,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[AnalysisResult, ...]:
    """Dispatch an analysis specification to its registered implementation."""
    raise UnsupportedAnalysisRecordError(
        f"No implementation registered for analysis type: {type(specification).__name__}"
    )


def register_analysis_capabilities() -> None:
    """Deterministically import and register all analysis capabilities exactly once."""
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True

    import datp_core.analysis.calibration.conformal  # noqa: F401
    import datp_core.analysis.calibration.quantile  # noqa: F401
    import datp_core.analysis.calibration.stability  # noqa: F401
    import datp_core.analysis.clustering.membership  # noqa: F401
    import datp_core.analysis.comparisons.association  # noqa: F401
    import datp_core.analysis.comparisons.effect_ratios  # noqa: F401
    import datp_core.analysis.comparisons.paired  # noqa: F401
    import datp_core.analysis.mechanisms.distributions  # noqa: F401
    import datp_core.analysis.mechanisms.operational  # noqa: F401
    import datp_core.analysis.mechanisms.temporal  # noqa: F401
    import datp_core.analysis.selection  # noqa: F401
    import datp_core.analysis.validation  # noqa: F401


class AnalysisRunner(BaseModel):
    """Resolves and executes the correct analysis implementation for each analysis record type."""

    model_config = ConfigDict(frozen=True)

    context: AnalysisExecutionContext

    def model_post_init(self, __context: object) -> None:
        register_analysis_capabilities()

    def run(
        self,
        specification: AnalysisRecord,
        *,
        cell: PairedAnalysisCell | None = None,
    ) -> tuple[AnalysisResult, ...]:
        return run_analysis(specification, self.context, cell)
