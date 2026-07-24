"""Pure descriptive-statistics primitives shared across capability modules: weighted means and
grouped dispersion (mean-of-group-std and std-of-group-means)."""

from __future__ import annotations

import numpy as np


def weighted_mean(values: list[tuple[int, int]]) -> float | None:
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None


def mean_group_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.mean([np.std([item[index] for item in group]) for group in groups])) if groups else None


def group_mean_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.std([np.mean([item[index] for item in group]) for group in groups])) if groups else None


__all__ = ["group_mean_std", "mean_group_std", "weighted_mean"]
