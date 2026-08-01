"""Deterministic descriptive summaries for seed and client level evidence."""

from dataclasses import dataclass
from math import isfinite

import numpy as np

from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, Seed


@dataclass(frozen=True, slots=True)
class DescriptiveSummary:
    evidence_role: EvidenceRole
    values: tuple[float, ...]
    available_count: int
    unavailable_count: int
    excluded_count: int
    mean: float | None
    median: float | None
    lower_quantile: float | None
    upper_quantile: float | None
    minimum: float | None
    maximum: float | None
    spread: float | None
    availability: AvailabilityStatus
    reason: str

    def __post_init__(self) -> None:
        if min(self.available_count, self.unavailable_count, self.excluded_count) < 0:
            raise ValueError("descriptive counts must be non-negative")
        if self.available_count != len(self.values):
            raise ValueError("available count must equal the numeric value count")
        if any(not isfinite(value) for value in self.values):
            raise ValueError("descriptive values must be finite")
        if self.availability is AvailabilityStatus.AVAILABLE:
            if not self.values or self.reason:
                raise ValueError("available descriptive summaries require values and no reason")
        elif self.reason == "":
            raise ValueError("unavailable descriptive summaries require a reason")


@dataclass(frozen=True, slots=True)
class NestedSeedSummary:
    seed: Seed
    replicate_values: tuple[float, ...]
    summary: MetricValue

    def __post_init__(self) -> None:
        if not self.replicate_values or any(not isfinite(value) for value in self.replicate_values):
            raise ValueError("nested summaries require finite replicate values")


@dataclass(frozen=True, slots=True)
class PairedDifferenceCounts:
    positive: int
    zero: int
    negative: int

    def __post_init__(self) -> None:
        if min(self.positive, self.zero, self.negative) < 0:
            raise ValueError("paired-difference counts must be non-negative")

    @property
    def total(self) -> int:
        return self.positive + self.zero + self.negative

    @property
    def positive_proportion(self) -> float | None:
        return self.positive / self.total if self.total else None


def summarize_values(
    values: tuple[float, ...],
    *,
    evidence_role: EvidenceRole,
    unavailable_count: int = 0,
    excluded_count: int = 0,
    lower_quantile: float = 0.25,
    upper_quantile: float = 0.75,
) -> DescriptiveSummary:
    if not 0 <= lower_quantile <= upper_quantile <= 1:
        raise ValueError("quantiles must be ordered values in [0, 1]")
    if unavailable_count < 0 or excluded_count < 0:
        raise ValueError("counts must be non-negative")
    if any(not isfinite(value) for value in values):
        raise ValueError("descriptive values must be finite")
    if not values:
        return DescriptiveSummary(
            evidence_role,
            (),
            0,
            unavailable_count,
            excluded_count,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            AvailabilityStatus.UNAVAILABLE,
            "no available values",
        )
    array = np.asarray(values, dtype=np.float64)
    minimum = float(np.min(array))
    maximum = float(np.max(array))
    return DescriptiveSummary(
        evidence_role,
        values,
        len(values),
        unavailable_count,
        excluded_count,
        float(np.mean(array)),
        float(np.median(array)),
        float(np.quantile(array, lower_quantile, method="linear")),
        float(np.quantile(array, upper_quantile, method="linear")),
        minimum,
        maximum,
        maximum - minimum,
        AvailabilityStatus.AVAILABLE,
        "",
    )


def summarize_nested_replicates(seed: Seed, replicate_values: tuple[float, ...]) -> NestedSeedSummary:
    if not replicate_values or any(not isfinite(value) for value in replicate_values):
        raise ValueError("nested replicate values must be finite and non-empty")
    return NestedSeedSummary(
        seed, replicate_values, MetricValue(float(np.mean(np.asarray(replicate_values, dtype=np.float64))))
    )


def count_paired_differences(values: tuple[float, ...]) -> PairedDifferenceCounts:
    if any(not isfinite(value) for value in values):
        raise ValueError("paired differences must be finite")
    return PairedDifferenceCounts(
        sum(value > 0 for value in values), sum(value == 0 for value in values), sum(value < 0 for value in values)
    )
