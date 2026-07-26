"""Pure descriptive-statistics primitives shared across capability modules."""

from __future__ import annotations

from collections.abc import Sequence

from datp_core.analysis.contracts import CountRatioObservation


def ratio_of_totals(observations: Sequence[CountRatioObservation]) -> float | None:
    """Ratio of total numerators to total denominators. Returns None when total denominator is zero."""
    total_denom = sum(obs.denominator for obs in observations)
    if not total_denom:
        return None
    return sum(obs.numerator for obs in observations) / total_denom
