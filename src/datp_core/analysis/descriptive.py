"""Deterministic descriptive summaries for seed- and client-level evidence."""

import numpy as np

from datp_core.analysis.models import MetricSeries, PairedDifferenceCounts
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, Ratio, Seed


class QuantileRange(StrictModel):
    lower: Ratio
    upper: Ratio

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE


class ObservationCounts(StrictModel):
    unavailable: int
    excluded: int


class DescriptiveStatistics(StrictModel):
    mean: MetricValue
    median: MetricValue
    lower_quantile_value: MetricValue
    upper_quantile_value: MetricValue
    minimum: MetricValue
    maximum: MetricValue

    @property
    def spread(self) -> MetricValue:
        return MetricValue(self.maximum.value - self.minimum.value)


class DescriptiveSummary(StrictModel):
    evidence_role: EvidenceRole
    values: MetricSeries
    counts: ObservationCounts
    quantiles: QuantileRange
    statistics: DescriptiveStatistics | None
    reason: str

    @property
    def available_count(self) -> int:
        return len(self.values)

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.values else AvailabilityStatus.UNAVAILABLE


class NestedSeedSummary(StrictModel):
    seed: Seed
    replicate_values: MetricSeries

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
