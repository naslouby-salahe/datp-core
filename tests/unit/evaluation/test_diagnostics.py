"""FPR dispersion, AUROC invariance, JS divergence, variance decomposition."""

import pytest

from datp_core.core.identifiers import ClientId
from datp_core.evaluation.diagnostics import (
    assert_auroc_invariant,
    calculate_fpr_dispersion,
    calculate_pairwise_js_divergence,
)
from datp_core.evaluation.enums import MetricStatus
from datp_core.evaluation.models import ClientScoreSeries


class TestCalculateFprDispersion:
    def test_population_std(self) -> None:
        result = calculate_fpr_dispersion((0.1, 0.2, 0.3), cv_instability_threshold=0.01, ddof=0)
        assert result.mean_fpr.value == pytest.approx(0.2)
        assert result.standard_deviation.value == pytest.approx((2 / 300) ** 0.5)
        assert result.coefficient_of_variation.value == pytest.approx(((2 / 300) ** 0.5) / 0.2)

    def test_sample_std_with_ddof_1(self) -> None:
        result = calculate_fpr_dispersion((0.1, 0.2, 0.3), cv_instability_threshold=0.01, ddof=1)
        assert result.standard_deviation.value == pytest.approx((2 / 200) ** 0.5)

    def test_zero_mean_cv_is_undefined(self) -> None:
        result = calculate_fpr_dispersion((0.0, 0.0), cv_instability_threshold=0.01, ddof=0)
        assert result.coefficient_of_variation.value is None
        assert result.coefficient_of_variation.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR

    def test_near_zero_fpr_keeps_numeric_cv_with_warning(self) -> None:
        result = calculate_fpr_dispersion((0.001, 0.003), cv_instability_threshold=0.01, ddof=0)
        assert result.coefficient_of_variation.value is not None
        assert result.coefficient_of_variation.status is MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR

    def test_empty_population_returns_all_unavailable(self) -> None:
        result = calculate_fpr_dispersion((), cv_instability_threshold=0.01, ddof=0)
        assert result.mean_fpr.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR
        assert result.worst_fpr.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR

    def test_single_client(self) -> None:
        result = calculate_fpr_dispersion((0.05,), cv_instability_threshold=0.01, ddof=0)
        assert result.mean_fpr.value == 0.05
        assert result.value_range.value == 0.0

    def test_ddof_equal_to_sample_count_raises(self) -> None:
        with pytest.raises(ValueError, match="ddof"):
            calculate_fpr_dispersion((0.1, 0.2), cv_instability_threshold=0.01, ddof=2)

    def test_negative_ddof_raises(self) -> None:
        with pytest.raises(ValueError, match="ddof"):
            calculate_fpr_dispersion((0.1, 0.2), cv_instability_threshold=0.01, ddof=-1)

    def test_rejects_non_finite_values(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            calculate_fpr_dispersion((0.1, float("inf")), cv_instability_threshold=0.01, ddof=0)

    def test_iqr_and_range(self) -> None:
        result = calculate_fpr_dispersion((0.1, 0.2, 0.3), cv_instability_threshold=0.01, ddof=0)
        assert result.iqr.value == pytest.approx(0.1)
        assert result.value_range.value == pytest.approx(0.2)
        assert result.worst_fpr.value == pytest.approx(0.3)


class TestAssertAurocInvariant:
    def test_pass_when_within_tolerance(self) -> None:
        assert_auroc_invariant((0.7, 0.7), tolerance=1e-12)

    def test_raises_when_exceeds_tolerance(self) -> None:
        with pytest.raises(ValueError, match="invariant"):
            assert_auroc_invariant((0.7, 0.71), tolerance=1e-12)

    def test_negative_tolerance_raises(self) -> None:
        with pytest.raises(ValueError, match="tolerance"):
            assert_auroc_invariant((0.7, 0.7), tolerance=-0.1)


class TestCalculatePairwiseJsDivergence:
    def test_shared_histogram_edges(self) -> None:
        divergence = calculate_pairwise_js_divergence(
            (
                ClientScoreSeries(client_id=ClientId("a"), scores=(0.0, 0.1)),
                ClientScoreSeries(client_id=ClientId("b"), scores=(0.9, 1.0)),
            ),
            histogram_bins=2,
            logarithm_base=2,
        )
        assert divergence == pytest.approx(1.0)

    def test_identical_distributions_yield_zero(self) -> None:
        divergence = calculate_pairwise_js_divergence(
            (
                ClientScoreSeries(client_id=ClientId("a"), scores=(0.1, 0.2)),
                ClientScoreSeries(client_id=ClientId("b"), scores=(0.1, 0.2)),
            ),
            histogram_bins=4,
            logarithm_base=2,
        )
        assert divergence == pytest.approx(0.0)

    def test_requires_at_least_two_clients(self) -> None:
        with pytest.raises(ValueError, match="at least two"):
            calculate_pairwise_js_divergence(
                (ClientScoreSeries(client_id=ClientId("a"), scores=(0.1, 0.2)),),
                histogram_bins=4,
                logarithm_base=2,
            )

    def test_requires_non_empty_scores(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ClientScoreSeries(client_id=ClientId("b"), scores=())
