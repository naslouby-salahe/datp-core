"""Pure statistical procedure primitives (BCa/percentile bootstrap, Wilcoxon, Spearman, linear
regression, Holm-Bonferroni correction) shared by every paired/temporal/association analysis.

Held out of ``analysis/execution.py`` -- which every analysis-family module depends on for the
``StatisticalAnalysisStageHandler`` dispatch table -- so that family modules can depend on this
pure use case without importing the stage handler.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from math import isfinite
from typing import cast

import numpy as np
from attrs import define
from scipy import stats

from datp_core.contracts.protocols import BootstrapMethod, StatisticalProfileRecord
from datp_core.core.identifiers import MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.core.values import Probability, Seed, TypedDomainRegistry


class StatisticalProcedureError(ValueError):
    """A locked statistical procedure cannot produce a scientifically valid result."""


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


def holm_adjust_p_values(values: Iterable[float]) -> tuple[float, ...]:
    """Apply the Holm step-down correction and return values in the original order."""
    p_values = tuple(float(value) for value in values)
    if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in p_values):
        raise StatisticalProcedureError("Holm correction requires finite p-values in [0, 1]")
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, (index, p_value) in enumerate(ordered):
        corrected = min(1.0, (len(p_values) - rank) * p_value)
        previous = max(previous, corrected)
        adjusted[index] = previous
    return tuple(adjusted)


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


@define(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: str

    def __attrs_post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError("Lower bound cannot be greater than upper bound")

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@define(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: str = "two-sided"


@define(frozen=True, slots=True, kw_only=True)
class LinearRegressionResult:
    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


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
            self._compute_spearman(predictor_values, outcome_values),
            self._compute_linear_regression(predictor_values, outcome_values),
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

    @staticmethod
    def _compute_spearman(predictor: np.ndarray, outcome: np.ndarray) -> HypothesisTestResult:
        statistic, p_value = cast("tuple[float, float]", stats.spearmanr(predictor, outcome))
        if not np.isfinite((statistic, p_value)).all():
            raise StatisticalProcedureError("Spearman correlation is undefined for the supplied observations")
        return HypothesisTestResult(
            test_name="spearman_correlation", statistic=float(statistic), p_value=float(p_value)
        )

    @staticmethod
    def _compute_linear_regression(predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
        slope, intercept, r_value, _, standard_error = cast(
            "tuple[float, float, float, float, float]", stats.linregress(predictor, outcome)
        )
        if not np.isfinite((slope, intercept, standard_error, r_value)).all():
            raise StatisticalProcedureError("Linear regression is undefined for the supplied observations")
        centered = predictor - np.mean(predictor)
        denominator = float(np.sum(centered**2))
        if math.isclose(denominator, 0.0, abs_tol=0.0):
            raise StatisticalProcedureError("Linear regression requires non-constant predictor observations")
        leverage = tuple(float((1.0 / len(predictor)) + (value**2 / denominator)) for value in centered)
        leave_one_out_slopes = tuple(
            cast(
                "tuple[float, float, float, float, float]",
                stats.linregress(np.delete(predictor, index), np.delete(outcome, index)),
            )[0]
            for index in range(len(predictor))
        )
        return LinearRegressionResult(
            slope=float(slope),
            intercept=float(intercept),
            standard_error=float(standard_error),
            r_squared=float(r_value**2),
            leverage=leverage,
            leave_one_out_slopes=leave_one_out_slopes,
        )
