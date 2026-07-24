"""Paired-seed inference: BCa/percentile bootstrap confidence intervals, Wilcoxon signed-rank
testing, and the matched-pairs rank-biserial effect size, composed behind
``StatisticalAnalysisUseCase``. Association inference (Spearman, linear regression) is exposed
through the same use case but its pure primitives live in ``statistics/association.py``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from math import isfinite
from typing import cast

import numpy as np
from scipy import stats

from datp_core.analysis.statistics.association import simple_linear_regression, spearman_correlation
from datp_core.analysis.statistics.models import (
    ConfidenceInterval,
    HypothesisTestResult,
    LinearRegressionResult,
    PairedSeedDifferenceRecord,
    StatisticalProcedureError,
)
from datp_core.contracts.protocols import BootstrapMethod, StatisticalProfileRecord
from datp_core.core.identifiers import MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.core.values import Probability, Seed, TypedDomainRegistry


def matched_pairs_rank_biserial_correlation(left: Iterable[float], right: Iterable[float]) -> float:
    """Return the signed-rank effect size for paired observations, with average tie ranks."""
    differences = tuple(float(a) - float(b) for a, b in zip(left, right, strict=True))
    if not differences or not all(isfinite(value) for value in differences):
        raise StatisticalProcedureError("Rank-biserial correlation requires finite paired observations")
    nonzero = tuple(value for value in differences if not math.isclose(value, 0.0, abs_tol=0.0))
    if not nonzero:
        raise StatisticalProcedureError("Rank-biserial correlation is undefined when all paired differences are zero")
    ranks = _average_ranks(tuple(abs(value) for value in nonzero))
    positive = sum(rank for difference, rank in zip(nonzero, ranks, strict=True) if difference > 0.0)
    negative = sum(rank for difference, rank in zip(nonzero, ranks, strict=True) if difference < 0.0)
    return (positive - negative) / (positive + negative)


def _average_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    ranks = [0.0] * len(values)
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for index, _ in ordered[start:end]:
            ranks[index] = average_rank
        start = end
    return tuple(ranks)


class StatisticalAnalysisUseCase:
    """Pure statistical analysis using native SciPy methods (BCa/percentile bootstrap, Wilcoxon,
    Spearman, linear regression)."""

    def __init__(self, profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]) -> None:
        self._profiles = profiles

    def analyze_paired_seed_differences(
        self,
        scores_policy_a: tuple[float, ...],
        scores_policy_b: tuple[float, ...],
        metric_name: str,
        policy_a_name: str,
        policy_b_name: str,
        statistical_profile_id: StatisticalProfileId,
        analysis_seed: Seed,
    ) -> PairedSeedDifferenceRecord:
        profile = self._profiles.get(statistical_profile_id)
        if (
            profile.method not in {BootstrapMethod.BCA_BOOTSTRAP, BootstrapMethod.PERCENTILE_BOOTSTRAP}
            or profile.resample_count is None
            or profile.confidence_level is None
        ):
            raise ValueError(
                f"Statistical profile '{statistical_profile_id.value}' is not an executable bootstrap profile"
            )
        arr_a = np.array(scores_policy_a, dtype=np.float64)
        arr_b = np.array(scores_policy_b, dtype=np.float64)
        if arr_a.shape != arr_b.shape:
            raise ValueError("Paired seed analysis requires equally sized policy score cohorts")
        diffs = arr_a - arr_b

        mean_diff = float(np.mean(diffs))
        assert profile.method is not None  # guaranteed by the method-not-in-{bca,percentile} guard above
        ci = self._compute_bca_bootstrap_ci(
            diffs,
            resample_count=profile.resample_count.value,
            confidence_level=profile.confidence_level.value,
            analysis_seed=analysis_seed.value,
            method=profile.method,
        )
        test_res = self._compute_wilcoxon_signed_rank(arr_a, arr_b) if len(arr_a) >= 5 else None

        return PairedSeedDifferenceRecord(
            metric_id=MetricId(metric_name),
            policy_a_id=ThresholdPolicyId(policy_a_name),
            policy_b_id=ThresholdPolicyId(policy_b_name),
            mean_difference=mean_diff,
            confidence_interval=ci,
            hypothesis_test=test_res,
            effect_size=matched_pairs_rank_biserial_correlation(arr_a, arr_b) if test_res is not None else None,
            resample_count=profile.resample_count.value,
            analysis_seed=analysis_seed,
        )

    def analyze_association(
        self, predictor: tuple[float, ...], outcome: tuple[float, ...]
    ) -> tuple[HypothesisTestResult, LinearRegressionResult]:
        predictor_values = np.array(predictor, dtype=np.float64)
        outcome_values = np.array(outcome, dtype=np.float64)
        if len(predictor_values) < 3 or predictor_values.shape != outcome_values.shape:
            raise ValueError("Association analysis requires at least three paired finite observations")
        if not np.isfinite(predictor_values).all() or not np.isfinite(outcome_values).all():
            raise ValueError("Association analysis requires finite observations")
        return (
            spearman_correlation(predictor_values, outcome_values),
            simple_linear_regression(predictor_values, outcome_values),
        )

    @staticmethod
    def _compute_wilcoxon_signed_rank(x: np.ndarray, y: np.ndarray) -> HypothesisTestResult:
        res = stats.wilcoxon(x, y, zero_method="wilcox", correction=True)
        statistic, p_value = cast("tuple[float, float]", res)
        return HypothesisTestResult(
            test_name="wilcoxon_signed_rank", statistic=float(statistic), p_value=float(p_value)
        )

    @staticmethod
    def _compute_bca_bootstrap_ci(
        data: np.ndarray,
        resample_count: int,
        confidence_level: float,
        analysis_seed: int,
        method: str,
    ) -> ConfidenceInterval:
        if method == BootstrapMethod.BCA_BOOTSTRAP and len(data) < 10:
            raise StatisticalProcedureError("BCa requires at least ten valid paired seed differences")
        if method == BootstrapMethod.PERCENTILE_BOOTSTRAP and len(data) < 2:
            raise StatisticalProcedureError("Percentile bootstrap requires at least two valid paired seed differences")
        if not np.isfinite(data).all():
            raise StatisticalProcedureError("BCa requires finite paired seed differences")
        if math.isclose(float(np.ptp(data)), 0.0, abs_tol=0.0):
            raise StatisticalProcedureError("BCa is degenerate for identical paired seed differences")

        try:
            res = stats.bootstrap(
                (data,),
                np.mean,
                n_resamples=resample_count,
                confidence_level=confidence_level,
                method="BCa" if method == BootstrapMethod.BCA_BOOTSTRAP else "percentile",
                rng=np.random.default_rng(analysis_seed),
            )
        except ValueError as exc:
            raise StatisticalProcedureError(f"BCa failed: {exc}") from exc
        if not np.isfinite((res.confidence_interval.low, res.confidence_interval.high)).all():
            raise StatisticalProcedureError("BCa produced a non-finite confidence interval")
        return ConfidenceInterval(
            lower_bound=float(res.confidence_interval.low),
            upper_bound=float(res.confidence_interval.high),
            confidence_level=Probability(confidence_level),
            method=method,
        )


__all__ = ["StatisticalAnalysisUseCase", "matched_pairs_rank_biserial_correlation"]
