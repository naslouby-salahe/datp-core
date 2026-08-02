from datp_core.analysis.descriptive import QuantileRange, count_paired_differences, summarize_nested_replicates, summarize_values
from datp_core.analysis.models import MetricSeries
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, Ratio, Seed

_DEFAULT_QUANTILES = QuantileRange(lower=Ratio(0.25), upper=Ratio(0.75))


def test_descriptive_summary_preserves_available_unavailable_and_excluded_counts() -> None:
    values: MetricSeries = (MetricValue(0.0), MetricValue(0.5), MetricValue(1.0))
    summary = summarize_values(
        values,
        evidence_role=EvidenceRole.CONFIRMATORY,
        unavailable_count=2,
        excluded_count=1,
        quantiles=_DEFAULT_QUANTILES,
    )

    assert summary.availability is AvailabilityStatus.AVAILABLE
    assert summary.mean == 0.5
    assert summary.median == 0.5
    assert summary.spread == 1.0
    assert (summary.available_count, summary.unavailable_count, summary.excluded_count) == (3, 2, 1)


def test_nested_replicates_are_summarized_within_seed_and_signs_preserve_zeroes() -> None:
    replicate_values: MetricSeries = (MetricValue(0.1), MetricValue(0.3), MetricValue(0.5))
    nested = summarize_nested_replicates(Seed(4), replicate_values)
    signs = count_paired_differences((MetricValue(0.4), MetricValue(0.0), MetricValue(-0.2), MetricValue(0.1)))

    assert nested.seed == Seed(4)
    assert nested.summary.value == 0.3
    assert (signs.positive, signs.zero, signs.negative, signs.positive_proportion) == (2, 1, 1, 0.5)
