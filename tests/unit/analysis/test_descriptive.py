import pytest

from datp_core.analysis.contrasts import MetricSeries
from datp_core.analysis.descriptive import (
    ObservationCounts,
    QuantileRange,
    count_paired_differences,
    summarize_values,
)
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values.counts import PairedObservationCount
from datp_core.domain.values.ratios import MetricValue, Ratio

_DEFAULT_QUANTILES = QuantileRange(lower=Ratio(0.25), upper=Ratio(0.75))


def test_descriptive_summary_preserves_typed_counts_and_statistics() -> None:
    values: MetricSeries = (
        MetricValue(0.0),
        MetricValue(0.5),
        MetricValue(1.0),
    )
    summary = summarize_values(
        values,
        evidence_role=EvidenceRole.CONFIRMATORY,
        counts=ObservationCounts(
            unavailable=PairedObservationCount(2),
            excluded=PairedObservationCount(1),
        ),
        quantiles=_DEFAULT_QUANTILES,
    )
    assert summary.availability is AvailabilityStatus.AVAILABLE
    assert summary.statistics is not None
    assert summary.statistics.mean == MetricValue(0.5)
    assert summary.statistics.spread == MetricValue(1.0)
    assert summary.available_count == PairedObservationCount(3)
    assert summary.reason is None


def test_empty_summary_is_explicitly_unavailable() -> None:
    summary = summarize_values(
        (),
        evidence_role=EvidenceRole.SUPPORTIVE,
        counts=ObservationCounts(
            unavailable=PairedObservationCount(1),
            excluded=PairedObservationCount(0),
        ),
        quantiles=_DEFAULT_QUANTILES,
    )
    assert summary.availability is AvailabilityStatus.UNAVAILABLE
    assert summary.statistics is None
    assert summary.reason == "no available values"


def test_quantile_range_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="lower quantile"):
        QuantileRange(lower=Ratio(0.75), upper=Ratio(0.25))


def test_sign_counts_preserve_zeroes_with_semantic_counts() -> None:
    result = count_paired_differences(
        (
            MetricValue(0.4),
            MetricValue(0.0),
            MetricValue(-0.2),
            MetricValue(0.1),
        )
    )
    assert (result.positive, result.zero, result.negative) == (
        PairedObservationCount(2),
        PairedObservationCount(1),
        PairedObservationCount(1),
    )
    assert result.positive_proportion == Ratio(0.5)
