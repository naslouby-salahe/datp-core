"""Base model and shared statistical primitives for all analysis contracts.

These live in a separate module to avoid circular imports: family contract modules
(calibration/contracts, comparisons/contracts, etc.) can import from _base without
pulling in contracts.py which re-imports from the family modules.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from datp_core.analysis.enums import ConfidenceIntervalMethod
from datp_core.analysis.errors import StatisticalProcedureError
from datp_core.core.numbers import Probability


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        arbitrary_types_allowed=True,
    )


class ConfidenceInterval(FrozenModel):
    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: ConfidenceIntervalMethod

    @model_validator(mode="after")
    def _validate_bounds(self) -> ConfidenceInterval:
        if self.lower_bound > self.upper_bound:
            raise StatisticalProcedureError(
                f"Confidence interval lower bound {self.lower_bound} exceeds upper bound {self.upper_bound}"
            )
        return self

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0
