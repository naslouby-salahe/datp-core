"""Pure descriptive-statistics primitives shared across capability modules: weighted means."""

from __future__ import annotations


def weighted_mean(values: list[tuple[int, int]]) -> float | None:
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None


__all__ = ["weighted_mean"]
