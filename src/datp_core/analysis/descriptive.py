"""Deterministic descriptive summaries for seed- and client-level evidence."""

import numpy as np
from pydantic import model_validator

from datp_core.analysis.models import MetricSeries, PairedDifferenceCounts
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, PairedObservationCount, Ratio


class QuantileRange(StrictModel):
    lower: Ratio
    upper: Ratio

    @model_validator(mode="after")
    def validate_range(self) -> "QuantileRange":
        if self.lower.value > self.upper.value:
            raise ValueError("descriptive lower quantile cannot exceed the upper quantile")
        return self


class ObservationCounts(StrictModel):
    unavailable: PairedObservationCount
    excluded: PairedObservationCount


class DescriptiveStatistics(StrictModel):
    mean: MetricValue
    median: MetricValue
    lower_quantile_value: MetricValue
    upper_quantile_value: MetricValue
    minimum: MetricValue
    maximum: MetricValue

    @model_validator(mode="after")
    def validate_order(self) -> "DescriptiveStatistics":
        values = (
            self.minimum.value,
            self.lower_quantile_value.value,
            self.median.value,
            self.upper_quantile_value.value,
            self.maximum.value,
        )
        if values != tuple(sorted(values)):
            raise ValueError("descriptive statistics must preserve their declared order")
        return self

    @property
    def spread(self) -> MetricValue:
        return MetricValue(self.maximum.value - self.minimum.value)


class DescriptiveSummary(StrictModel):
    evidence_role: EvidenceRole
    values: MetricSeries
    counts: ObservationCounts
    quantiles: QuantileRange
    statistics: DescriptiveStatistics | None
    reason: str | None

    @model_validator(mode="after")
    def validate_summary(self) -> "DescriptiveSummary":
        if self.values:
            if self.statistics is None or self.reason is not None:
                raise ValueError("available descriptive values require statistics and no reason")
        elif self.statistics is not None or self.reason is None:
            raise ValueError("unavailable descriptive values require no statistics and an explicit reason")
        return self

    @property
    def available_count(self) -> PairedObservationCount:
        return PairedObservationCount(len(self.values))

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.values else AvailabilityStatus.UNAVAILABLE


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
    return DescriptiveSummary(
        evidence_role=evidence_role,
        values=values,
        counts=counts,
        quantiles=quantiles,
        statistics=DescriptiveStatistics(
            mean=MetricValue(float(np.mean(array))),
            median=MetricValue(float(np.median(array))),
            lower_quantile_value=MetricValue(float(np.quantile(array, quantiles.lower.value, method="linear"))),
            upper_quantile_value=MetricValue(float(np.quantile(array, quantiles.upper.value, method="linear"))),
            minimum=MetricValue(float(np.min(array))),
            maximum=MetricValue(float(np.max(array))),
        ),
        reason=None,
    )


def count_paired_differences(values: MetricSeries) -> PairedDifferenceCounts:
    return PairedDifferenceCounts(
        positive=PairedObservationCount(sum(value.value > 0.0 for value in values)),
        zero=PairedObservationCount(sum(value.value == 0.0 for value in values)),
        negative=PairedObservationCount(sum(value.value < 0.0 for value in values)),
    )


def _metric_array(values: MetricSeries) -> np.ndarray:
    array = np.fromiter((value.value for value in values), dtype=np.float64, count=len(values))
    if np.any(~np.isfinite(array)):
        raise ValueError("metric values must be finite")
    return array
