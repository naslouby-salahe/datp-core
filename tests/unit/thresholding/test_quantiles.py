import math

import numpy as np
import pytest
from tests.unit.thresholding.helpers import client_scores

from datp_core.domain.enums import QuantileInterpolationSemantics
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import ConformalRankIndex, RowCount
from datp_core.domain.values.ratios import CoverageTarget, Quantile, SummaryCoefficient, ThresholdValue
from datp_core.thresholding.quantiles import (
    achieved_benign_exceedance,
    conformal_rank_index,
    exact_empirical_quantile,
    finite_sample_conformal_threshold,
    fixed_coefficient_threshold,
    gaussian_matched_exceedance_threshold,
    local_quantile,
    quantile_interpolation_semantics,
    sample_weighted_mean,
    unweighted_mean,
)


def test_exact_empirical_quantile_matches_numpy_linear_interpolation() -> None:
    scores = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = exact_empirical_quantile(scores, Quantile(0.5))
    assert result.value == float(np.quantile(scores, 0.5, method="linear"))


def test_exact_empirical_quantile_rejects_empty_array() -> None:
    def call():
        return exact_empirical_quantile(np.asarray([], dtype=np.float64), Quantile(0.5))

    with pytest.raises(ScientificContractError, match="non-empty"):
        call()


def test_quantile_interpolation_semantics_is_the_locked_numpy_linear_rule() -> None:
    assert quantile_interpolation_semantics() is QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR


def test_unweighted_mean_matches_arithmetic_mean() -> None:
    assert unweighted_mean((1.0, 2.0, 3.0)) == 2.0


def test_sample_weighted_mean_matches_manual_computation() -> None:
    result = sample_weighted_mean((1.0, 3.0), (1.0, 3.0))
    assert result == (1.0 * 1.0 + 3.0 * 3.0) / 4.0


def test_conformal_rank_index_matches_classical_split_conformal_formula() -> None:
    coverage = CoverageTarget(0.95)
    assert conformal_rank_index(RowCount(99), coverage) == ConformalRankIndex(math.ceil(100 * 0.95))


def test_finite_sample_conformal_threshold_selects_the_expected_order_statistic() -> None:
    scores = np.arange(1.0, 101.0)
    threshold, rank_index, effective_quantile, tie_count = finite_sample_conformal_threshold(
        scores, CoverageTarget(0.95)
    )
    assert rank_index == ConformalRankIndex(96)
    assert threshold.value == 96.0
    assert effective_quantile == 96 / 100
    assert tie_count == 0


def test_finite_sample_conformal_threshold_is_infeasible_for_too_few_scores() -> None:
    scores = np.array([1.0, 2.0])

    def call():
        return finite_sample_conformal_threshold(scores, CoverageTarget(0.95))

    with pytest.raises(ScientificContractError, match="exceeds the available calibration count"):
        call()


def test_achieved_benign_exceedance_is_the_fraction_strictly_above_threshold() -> None:
    scores = np.array([1.0, 2.0, 3.0, 4.0])
    exceedance = achieved_benign_exceedance(scores, ThresholdValue(2.0))
    assert exceedance == 0.5


def test_gaussian_matched_exceedance_threshold_at_the_median_returns_the_mean() -> None:
    result = gaussian_matched_exceedance_threshold(mean=10.0, variance=4.0, quantile=Quantile(0.5))
    assert math.isclose(result.value, 10.0, abs_tol=1e-9)


def test_fixed_coefficient_threshold_matches_mean_plus_k_std() -> None:
    result = fixed_coefficient_threshold(mean=10.0, variance=4.0, coefficient=SummaryCoefficient(2.0))
    assert result.value == 10.0 + 2.0 * 2.0


def test_local_quantile_uses_the_locked_interpolation_semantics() -> None:
    scores = client_scores("client_a", (1.0, 2.0, 3.0, 4.0, 5.0))
    result = local_quantile(scores, Quantile(0.5))
    assert result.diagnostic.quantile_interpolation is QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR
    assert result.calibration_count.value == 5
