"""Pure descriptive-statistics primitives shared across capability modules."""

from __future__ import annotations


def weighted_mean(values: list[tuple[int, int]]) -> float | None:
    """Weighted mean of (value, weight) pairs. Returns None when total weight is zero."""
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None
