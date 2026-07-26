"""Unit tests for inference and Holm correction."""

from __future__ import annotations

import pytest

from datp_core.analysis.contracts import ConfidenceInterval, PairedThresholdAnalysisResult
from datp_core.analysis.enums import AlternativeHypothesis, ConfidenceIntervalMethod
from datp_core.analysis.errors import StatisticalProcedureError
from datp_core.analysis.statistics.inference import (
    apply_holm_correction,
    holm_adjust_p_values,
    matched_pairs_rank_biserial_correlation,
)
from datp_core.core.identifiers import AnalysisLabel, MetricId, ThresholdPolicyId
from datp_core.core.seeding import Seed
from datp_core.core.numbers import Probability


def test_matched_pairs_rank_biserial_correlation_numeric() -> None:
    left = (1.0, 2.0, 3.0, 4.0, 5.0)
    right = (0.5, 1.5, 2.5, 3.5, 4.5)
    r_b = matched_pairs_rank_biserial_correlation(left, right)
    assert r_b == 1.0

    left_ties = (1.0, 2.0, 3.0)
    right_ties = (1.0, 2.0, 3.0)
    assert matched_pairs_rank_biserial_correlation(left_ties, right_ties) == 0.0


def test_holm_adjust_p_values() -> None:
    p_vals = (0.01, 0.04, 0.03)
    adjusted = holm_adjust_p_values(p_vals)
    assert len(adjusted) == 3
    assert adjusted[0] == pytest.approx(0.03)  # 0.01 * 3
    assert adjusted[2] == pytest.approx(0.06)  # 0.03 * 2
    assert adjusted[1] == pytest.approx(0.06)  # max(0.06, 0.04 * 1)


def test_apply_holm_correction_on_results() -> None:
    ci = ConfidenceInterval(
        lower_bound=0.01,
        upper_bound=0.05,
        confidence_level=Probability(0.95),
        method=ConfidenceIntervalMethod.BCA_BOOTSTRAP,
    )
    r1 = PairedThresholdAnalysisResult(
        analysis_label=AnalysisLabel("a1"),
        metric=MetricId("cv_fpr"),
        first_threshold_policy=ThresholdPolicyId("p1"),
        second_threshold_policy=ThresholdPolicyId("p2"),
        training_seeds=(Seed(1),),
        first_seed_values=(0.1,),
        second_seed_values=(0.08,),
        first_mean=0.1,
        second_mean=0.08,
        mean_difference=0.02,
        confidence_interval=ci,
        p_value=0.01,
        rank_biserial=1.0,
        resample_count=100,
        analysis_seed=Seed(10),
        seed_differences=(0.02,),
        sign_consistency=1.0,
        zero_difference_count=0,
        negative_difference_count=0,
    )
    r2 = PairedThresholdAnalysisResult(
        analysis_label=AnalysisLabel("a2"),
        metric=MetricId("cv_fpr"),
        first_threshold_policy=ThresholdPolicyId("p1"),
        second_threshold_policy=ThresholdPolicyId("p2"),
        training_seeds=(Seed(1),),
        first_seed_values=(0.1,),
        second_seed_values=(0.08,),
        first_mean=0.1,
        second_mean=0.08,
        mean_difference=0.02,
        confidence_interval=ci,
        p_value=0.04,
        rank_biserial=1.0,
        resample_count=100,
        analysis_seed=Seed(10),
        seed_differences=(0.02,),
        sign_consistency=1.0,
        zero_difference_count=0,
        negative_difference_count=0,
    )

    corrected = apply_holm_correction([r1, r2])
    assert len(corrected) == 2
    assert isinstance(corrected[0], PairedThresholdAnalysisResult)
    assert corrected[0].holm_adjusted_p_value == pytest.approx(0.02)
    assert isinstance(corrected[1], PairedThresholdAnalysisResult)
    assert corrected[1].holm_adjusted_p_value == pytest.approx(0.04)
