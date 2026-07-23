"""Application use case for statistical hypothesis testing and BCa confidence intervals."""

from __future__ import annotations

from typing import cast

import numpy as np
from scipy import stats

from datp_core.domain.catalogue import StatisticalProfileRecord
from datp_core.domain.identifiers import MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.domain.statistics import (
    ConfidenceInterval,
    HypothesisTestResult,
    LinearRegressionResult,
    PairedSeedDifferenceRecord,
    StatisticalProcedureError,
    matched_pairs_rank_biserial_correlation,
)
from datp_core.domain.values import Probability, Seed, TypedDomainRegistry


class StatisticalAnalysisUseCase:
    """Application use case for statistical analysis using native SciPy methods."""

    def __init__(
        self,
        profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord],
    ) -> None:
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
            profile.method not in {"bca_bootstrap", "percentile_bootstrap"}
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
        statistic, p_value = cast(tuple[float, float], res)
        return HypothesisTestResult(
            test_name="wilcoxon_signed_rank", statistic=float(statistic), p_value=float(p_value)
        )

    @staticmethod
    def _compute_bca_bootstrap_ci(
        data: np.ndarray, resample_count: int, confidence_level: float, analysis_seed: int, method: str
    ) -> ConfidenceInterval:
        if method == "bca_bootstrap" and len(data) < 10:
            raise StatisticalProcedureError("BCa requires at least ten valid paired seed differences")
        if method == "percentile_bootstrap" and len(data) < 2:
            raise StatisticalProcedureError("Percentile bootstrap requires at least two valid paired seed differences")
        if not np.isfinite(data).all():
            raise StatisticalProcedureError("BCa requires finite paired seed differences")
        if np.ptp(data) == 0.0:
            raise StatisticalProcedureError("BCa is degenerate for identical paired seed differences")

        try:
            res = stats.bootstrap(
                (data,),
                np.mean,
                n_resamples=resample_count,
                confidence_level=confidence_level,
                method="BCa" if method == "bca_bootstrap" else "percentile",
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
        statistic, p_value = cast(tuple[float, float], stats.spearmanr(predictor, outcome))
        if not np.isfinite((statistic, p_value)).all():
            raise StatisticalProcedureError("Spearman correlation is undefined for the supplied observations")
        return HypothesisTestResult(
            test_name="spearman_correlation", statistic=float(statistic), p_value=float(p_value)
        )

    @staticmethod
    def _compute_linear_regression(predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
        slope, intercept, r_value, _, standard_error = cast(
            tuple[float, float, float, float, float], stats.linregress(predictor, outcome)
        )
        if not np.isfinite((slope, intercept, standard_error, r_value)).all():
            raise StatisticalProcedureError("Linear regression is undefined for the supplied observations")
        centered = predictor - np.mean(predictor)
        denominator = float(np.sum(centered**2))
        if denominator == 0.0:
            raise StatisticalProcedureError("Linear regression requires non-constant predictor observations")
        leverage = tuple(float((1.0 / len(predictor)) + (value**2 / denominator)) for value in centered)
        leave_one_out_slopes = tuple(
            cast(
                tuple[float, float, float, float, float],
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
