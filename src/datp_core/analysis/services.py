"""Small deterministic statistical primitives with typed degenerate outcomes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisEstimate:
    estimate: float
    count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class DegenerateAnalysis:
    reason: str


def paired_mean_delta(first: tuple[float, ...], second: tuple[float, ...]) -> AnalysisEstimate | DegenerateAnalysis:
    if len(first) != len(second) or not first:
        return DegenerateAnalysis(reason="paired analysis requires a non-empty equal-length seed cohort")
    deltas = tuple(left - right for left, right in zip(first, second, strict=True))
    if any(value != value for value in deltas):
        return DegenerateAnalysis(reason="paired values must be finite")
    return AnalysisEstimate(estimate=sum(deltas) / len(deltas), count=len(deltas))
