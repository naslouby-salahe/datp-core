from datp_core.analysis.descriptive import count_paired_differences, summarize_nested_replicates, summarize_values
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import Seed


def test_descriptive_summary_preserves_available_unavailable_and_excluded_counts() -> None:
    summary = summarize_values(
        (0.0, 0.5, 1.0),
        evidence_role=EvidenceRole.CONFIRMATORY,
        unavailable_count=2,
        excluded_count=1,
    )

    assert summary.availability is AvailabilityStatus.AVAILABLE
    assert summary.mean == 0.5
    assert summary.median == 0.5
    assert summary.spread == 1.0
    assert (summary.available_count, summary.unavailable_count, summary.excluded_count) == (3, 2, 1)


def test_nested_replicates_are_summarized_within_seed_and_signs_preserve_zeroes() -> None:
    nested = summarize_nested_replicates(Seed(4), (0.1, 0.3, 0.5))
    signs = count_paired_differences((0.4, 0.0, -0.2, 0.1))

    assert nested.seed == Seed(4)
    assert nested.summary.value == 0.3
    assert (signs.positive, signs.zero, signs.negative, signs.positive_proportion) == (2, 1, 1, 0.5)
