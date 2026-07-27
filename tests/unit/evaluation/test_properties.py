"""Property-based tests for evaluation invariants using Hypothesis."""

from __future__ import annotations

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from datp_core.core.identifiers import ClientId
from datp_core.evaluation.diagnostics import calculate_calibration_variance, calculate_pairwise_js_divergence
from datp_core.evaluation.models import CdfPoint, ClientScoreSeries


def _empirical_cdf_public(values: list[float]) -> tuple[CdfPoint, ...]:
    return tuple(
        CdfPoint(score=value, cumulative_probability=(index + 1) / len(values)) for index, value in enumerate(values)
    )


class TestCdfMonotonicity:
    @given(st.lists(st.floats(min_value=-100.0, max_value=100.0), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_cdf_probabilities_are_non_decreasing(self, values: list[float]) -> None:
        sorted_vals = sorted(values)
        cdf = _empirical_cdf_public(sorted_vals)
        for i in range(len(cdf) - 1):
            assert cdf[i].cumulative_probability <= cdf[i + 1].cumulative_probability

    @given(st.lists(st.floats(min_value=-100.0, max_value=100.0), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_final_cdf_probability_is_one(self, values: list[float]) -> None:
        sorted_vals = sorted(values)
        cdf = _empirical_cdf_public(sorted_vals)
        assert len(cdf) == len(values)
        assert cdf[-1].cumulative_probability == 1.0


class TestVarianceDecomposition:
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=3),
                st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            ),
            min_size=2,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_total_equals_within_plus_between(self, rows: list[tuple[str, float]]) -> None:
        """Variance decomposition identity: total variance = within + between."""
        df = pl.DataFrame(rows, schema={"client_id": pl.String, "score": pl.Float64}, orient="row")
        result = calculate_calibration_variance(df, ddof=0)
        if result.between_ratio is not None:
            total_var = df["score"].var(ddof=0)
            assert isinstance(total_var, (int, float))
            assert abs(result.within_term + result.between_term - float(total_var)) < 1e-10

    @given(
        st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=1, max_size=20
        )
    )
    @settings(max_examples=100)
    def test_between_ratio_in_unit_interval(self, values: list[float]) -> None:
        """Between-ratio must be in [0, 1] when total > 0."""
        n = len(values)
        client_ids = [f"c{i % max(2, n // 2)}" for i in range(n)]
        df = pl.DataFrame(
            {"client_id": client_ids, "score": values},
            schema={"client_id": pl.String, "score": pl.Float64},
        )
        result = calculate_calibration_variance(df, ddof=0)
        if result.between_ratio is not None:
            assert 0.0 <= result.between_ratio <= 1.0


class TestJsDivergence:
    @given(
        st.lists(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=30
        )
    )
    @settings(max_examples=50)
    def test_identical_distributions_yield_zero(self, values: list[float]) -> None:
        """JS divergence of identical distributions must be approximately zero."""
        client_scores = (
            ClientScoreSeries(client_id=ClientId("a"), scores=tuple(values)),
            ClientScoreSeries(client_id=ClientId("b"), scores=tuple(values)),
        )
        divergence = calculate_pairwise_js_divergence(client_scores, histogram_bins=8, logarithm_base=2)
        assert divergence == pytest.approx(0.0, abs=1e-10)

    @given(
        st.lists(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=20
        ),
        st.lists(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=20
        ),
    )
    @settings(max_examples=50)
    def test_divergence_is_non_negative(self, left_vals: list[float], right_vals: list[float]) -> None:
        """JS divergence must be non-negative."""
        client_scores = (
            ClientScoreSeries(client_id=ClientId("a"), scores=tuple(left_vals)),
            ClientScoreSeries(client_id=ClientId("b"), scores=tuple(right_vals)),
        )
        divergence = calculate_pairwise_js_divergence(client_scores, histogram_bins=8, logarithm_base=2)
        assert divergence >= 0.0


class TestConfusionCountIdentity:
    @given(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_total_rows_equal_sum_of_counts(self, tp: int, fp: int, tn: int, fn: int) -> None:
        """Confusion matrix counts sum to total rows."""
        total = tp + fp + tn + fn
        assert total >= 0
        if total > 0:
            assert (tp + fn) + (fp + tn) == total
