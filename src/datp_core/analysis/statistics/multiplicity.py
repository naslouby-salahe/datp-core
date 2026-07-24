"""Multiple-comparisons correction."""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

from datp_core.analysis.statistics.models import StatisticalProcedureError


def holm_adjust_p_values(values: Iterable[float]) -> tuple[float, ...]:
    """Apply the Holm step-down correction and return values in the original order."""
    p_values = tuple(float(value) for value in values)
    if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in p_values):
        raise StatisticalProcedureError("Holm correction requires finite p-values in [0, 1]")
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, (index, p_value) in enumerate(ordered):
        corrected = min(1.0, (len(p_values) - rank) * p_value)
        previous = max(previous, corrected)
        adjusted[index] = previous
    return tuple(adjusted)


__all__ = ["holm_adjust_p_values"]
