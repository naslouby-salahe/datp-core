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
class DescriptiveSummary:
    evidence_role: EvidenceRole
    values: MetricSeries
    unavailable_count: int
    excluded_count: int
    quantiles: QuantileRange
    mean: MetricValue | None
    median: MetricValue | None
    lower_quantile_value: MetricValue | None
    upper_quantile_value: MetricValue | None
    minimum: MetricValue | None
    maximum: MetricValue | None
    reason: str

    def __post_init__(self) -> None:
        if min(self.unavailable_count, self.excluded_count) < 0:
            raise ValueError("descriptive counts must be non-negative")
        if any(not isfinite(value.value) for value in self.values):
            raise ValueError("descriptive values must be finite")

        statistics = (
            self.mean,
            self.median,
            self.lower_quantile_value,
            self.upper_quantile_value,
            self.minimum,
            self.maximum,
        )
        if self.values:
            if any(value is None for value in statistics) or self.reason:
                raise ValueError("available descriptive summaries require complete statistics and no reason")
            if self.minimum is not None and self.maximum is not None and self.minimum.value > self.maximum.value:
                raise ValueError("descriptive minimum cannot exceed maximum")
        elif any(value is not None for value in statistics) or not self.reason:
            raise ValueError("unavailable descriptive summaries require no statistics and an explicit reason")

    @property
    def available_count(self) -> int:
        return len(self.values)

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.values else AvailabilityStatus.UNAVAILABLE

    @property
    def spread(self) -> MetricValue | None:
        if self.minimum is None or self.maximum is None:
            return None
        return MetricValue(self.maximum.value - self.minimum.value)


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
    unavailable_count: int,
    excluded_count: int,
    quantiles: QuantileRange,
) -> DescriptiveSummary:
    if unavailable_count < 0 or excluded_count < 0:
        raise ValueError("counts must be non-negative")
    if not values:
        return DescriptiveSummary(
            evidence_role=evidence_role,
            values=(),
            unavailable_count=unavailable_count,
            excluded_count=excluded_count,
            quantiles=quantiles,
            mean=None,
            median=None,
            lower_quantile_value=None,
            upper_quantile_value=None,
            minimum=None,
            maximum=None,
            reason="no available values",
        )

    array = _metric_array(values)
    return DescriptiveSummary(
        evidence_role=evidence_role,
        values=values,
        unavailable_count=unavailable_count,
        excluded_count=excluded_count,
        quantiles=quantiles,
        mean=MetricValue(float(np.mean(array))),
        median=MetricValue(float(np.median(array))),
        lower_quantile_value=MetricValue(float(np.quantile(array, quantiles.lower.value, method="linear"))),
        upper_quantile_value=MetricValue(float(np.quantile(array, quantiles.upper.value, method="linear"))),
        minimum=MetricValue(float(np.min(array))),
        maximum=MetricValue(float(np.max(array))),
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
