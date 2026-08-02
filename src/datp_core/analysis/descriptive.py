"""Deterministic descriptive summaries for seed- and client-level evidence."""

from dataclasses import dataclass
from math import isfinite

import numpy as np

from datp_core.analysis.models import MetricSeries, PairedDifferenceCounts
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, Ratio, Seed


@dataclass(frozen=True, slots=True)
class QuantileRange:
    lower: Ratio
    upper: Ratio

    def __post_init__(self) -> None:
        if self.lower.value > self.upper.value:
            raise ValueError("quantile bounds must be ordered")


@dataclass(frozen=True, slots=True)
class ObservationCounts:
    unavailable: int
    excluded: int

    def __post_init__(self) -> None:
        if self.unavailable < 0 or self.excluded < 0:
            raise ValueError("observation counts must be non-negative")


@dataclass(frozen=True, slots=True)
class DescriptiveStatistics:
    mean: MetricValue
    median: MetricValue
    lower_quantile_value: MetricValue
    upper_quantile_value: MetricValue
    minimum: MetricValue
    maximum: MetricValue

    def __post_init__(self) -> None:
        if self.minimum.value > self.maximum.value:
            raise ValueError("descriptive minimum cannot exceed maximum")

    @property
    def spread(self) -> MetricValue:
        return MetricValue(self.maximum.value - self.minimum.value)


@dataclass(frozen=True, slots=True)
class DescriptiveSummary:
    evidence_role: EvidenceRole
    values: MetricSeries
    counts: ObservationCounts
    quantiles: QuantileRange
    statistics: DescriptiveStatistics | None
    reason: str

    def __post_init__(self) -> None:
        if any(not isfinite(value.value) for value in self.values):
            raise ValueError("descriptive values must be finite")
        if self.values:
            if self.statistics is None or self.reason:
                raise ValueError("available descriptive summaries require complete statistics and no reason")
        elif self.statistics is not None or not self.reason:
            raise ValueError("unavailable descriptive summaries require no statistics and an explicit reason")

    @property
    def available_count(self) -> int:
        return len(self.values)

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.values else AvailabilityStatus.UNAVAILABLE


@dataclass(frozen=True, slots=True)
class NestedSeedSummary:
    seed: Seed
    replicate_values: MetricSeries

    def __post_init__(self) -> None:
        if not self.replicate_values or any(not isfinite(value.value) for value in self.replicate_values):
            raise ValueError("nested summaries require finite non-empty replicate values")

    @property
    def summary(self) -> MetricValue:
        return MetricValue(float(np.mean(_metric_array(self.replicate_values))))


def summarize_values(
    values: MetricSeries,
    *,
    evidence_role: EvidenceRole,
    counts: ObservationCounts,
    quantiles: QuantileRange,
) -> DescriptiveSummary:
    if not values:
        return DescriptiveSummary(
            evidence_role=evidence_role,
            values=(),
            counts=counts,
            quantiles=quantiles,
            statistics=None,
            reason="no available values",
        )

    array = _metric_array(values)
    statistics = DescriptiveStatistics(
        mean=MetricValue(float(np.mean(array))),
        median=MetricValue(float(np.median(array))),
        lower_quantile_value=MetricValue(float(np.quantile(array, quantiles.lower.value, method="linear"))),
        upper_quantile_value=MetricValue(float(np.quantile(array, quantiles.upper.value, method="linear"))),
        minimum=MetricValue(float(np.min(array))),
        maximum=MetricValue(float(np.max(array))),
    )
    return DescriptiveSummary(
        evidence_role=evidence_role,
        values=values,
        counts=counts,
        quantiles=quantiles,
        statistics=statistics,
        reason="",
    )


def summarize_nested_replicates(
    seed: Seed,
    replicate_values: MetricSeries,
) -> NestedSeedSummary:
    return NestedSeedSummary(seed=seed, replicate_values=replicate_values)


def count_paired_differences(
    values: MetricSeries,
) -> PairedDifferenceCounts:
    return PairedDifferenceCounts(
        positive=sum(value.value > 0.0 for value in values),
        zero=sum(value.value == 0.0 for value in values),
        negative=sum(value.value < 0.0 for value in values),
    )


def _metric_array(values: MetricSeries) -> np.ndarray:
    array = np.fromiter(
        (value.value for value in values),
        dtype=np.float64,
        count=len(values),
    )
    if np.any(~np.isfinite(array)):
        raise ValueError("metric values must be finite")
    return array
