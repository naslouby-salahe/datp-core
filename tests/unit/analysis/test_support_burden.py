import pytest

from datp_core.analysis.mechanisms.support_burden import (
    CalibrationSupportBurdenSeedEvidence,
    SupportAssociationAvailability,
    _average_ranks,
    _spearman,
    summarize_calibration_support_burden,
)
from datp_core.core.numeric import MetricValue, Seed


def test_support_burden_spearman_uses_average_ranks_for_ties() -> None:
    assert _average_ranks((1.0, 1.0, 3.0)) == (1.5, 1.5, 3.0)
    assert _spearman((1.0, 1.0, 3.0), (1.0, 1.0, 3.0)) == pytest.approx(1.0)


def test_support_burden_spearman_marks_constant_input_unavailable() -> None:
    assert _spearman((1.0, 1.0, 1.0), (1.0, 2.0, 3.0)) is None


def test_support_burden_campaign_retains_seed_direction_counts() -> None:
    summary = summarize_calibration_support_burden(
        (
            _evidence(seed=1, value=-0.5),
            _evidence(seed=2, value=0.0),
            _evidence(seed=3, value=0.5),
        )
    )

    assert summary.support_fpr.negative_count.value == 1
    assert summary.support_fpr.zero_count.value == 1
    assert summary.support_fpr.positive_count.value == 1
    assert summary.support_fpr.median is not None and summary.support_fpr.median.value == 0.0


def test_support_burden_rejects_available_status_without_both_statistics() -> None:
    with pytest.raises(ValueError, match="requires both Spearman"):
        CalibrationSupportBurdenSeedEvidence(
            seed=Seed(1),
            clients=(),
            support_fpr_spearman=MetricValue(0.5),
            support_relief_spearman=None,
            availability=SupportAssociationAvailability.AVAILABLE,
            reason=None,
        )


def _evidence(*, seed: int, value: float) -> CalibrationSupportBurdenSeedEvidence:
    return CalibrationSupportBurdenSeedEvidence(
        seed=Seed(seed),
        clients=(),
        support_fpr_spearman=MetricValue(value),
        support_relief_spearman=MetricValue(value),
        availability=SupportAssociationAvailability.AVAILABLE,
        reason=None,
    )
