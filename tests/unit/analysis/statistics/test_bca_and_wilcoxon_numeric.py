"""The BCa bootstrap CI and Wilcoxon signed-rank primitives compute the exact expected numbers.

Complements test_bca_degeneracy.py (which only exercises rejection of invalid input) by locking
in the actual computed statistic/CI for known input, so a change to the scipy call parameters
(zero_method, correction, method, rng derivation, or an x/y argument-order swap) is caught here
rather than only by an assertion that "a result exists".
"""

import numpy as np
import pytest

from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase


def test_wilcoxon_signed_rank_matches_the_documented_scipy_computation() -> None:
    x = np.array([12.0, 15.0, 9.0, 18.0, 20.0, 14.0, 22.0, 11.0, 17.0, 19.0])
    y = np.array([10.0, 14.0, 9.0, 15.0, 22.0, 11.0, 19.0, 13.0, 16.0, 15.0])

    result = StatisticalAnalysisUseCase._compute_wilcoxon_signed_rank(x, y)

    assert result.test_name == "wilcoxon_signed_rank"
    assert result.statistic == pytest.approx(8.0)
    assert result.p_value == pytest.approx(0.0859375)


def test_bca_bootstrap_ci_matches_the_documented_scipy_computation_for_a_fixed_seed() -> None:
    data = np.array([2.0, 3.0, -1.0, 1.5, -2.0, 4.0, 0.5, 2.5, -0.5, 3.5, 1.0, -1.5])

    ci = StatisticalAnalysisUseCase._compute_bca_bootstrap_ci(
        data, resample_count=2000, confidence_level=0.95, analysis_seed=300, method="bca_bootstrap"
    )

    assert ci.method == "bca_bootstrap"
    assert ci.lower_bound == pytest.approx(-0.041666666666666664)
    assert ci.upper_bound == pytest.approx(2.125)
    assert ci.excludes_zero_positive is False
