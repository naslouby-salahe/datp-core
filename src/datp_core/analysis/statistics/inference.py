"""Paired-seed inference: BCa/percentile bootstrap, Wilcoxon signed-rank, rank-biserial effect
size, Holm-Bonferroni correction, composed behind ``StatisticalAnalysisUseCase``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from math import isfinite

import numpy as np
import pandas as pd
import pingouin as pg
from scipy import stats

from datp_core.analysis.comparisons.contracts import PairedThresholdAnalysisResult
from datp_core.analysis.contracts import (
    AnalysisResult,
    ConfidenceInterval,
    HypothesisTestResult,
    LinearRegressionResult,
    PairedSeedDifferenceRecord,
)
from datp_core.analysis.enums import AlternativeHypothesis, ConfidenceIntervalMethod, HypothesisTestName
from datp_core.analysis.errors import StatisticalProcedureError
from datp_core.analysis.statistics.association import simple_linear_regression, spearman_correlation
from datp_core.config.statistical_profiles import BootstrapMethod, StatisticalProfileRecord
from datp_core.core.identifiers import MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.core.registry import TypedDomainRegistry
from datp_core.core.seeding import Seed


def matched_pairs_rank_biserial_correlation(left: Iterable[float], right: Iterable[float]) -> float:
    """Signed-rank effect size for paired observations using Pingouin."""
    differences = tuple(float(a) - float(b) for a, b in zip(left, right, strict=True))
    if not differences or not all(isfinite(value) for value in differences):
        raise StatisticalProcedureError("Rank-biserial correlation requires finite paired observations")
    nonzero = tuple(value for value in differences if not math.isclose(value, 0.0, abs_tol=0.0))
    if not nonzero:
        return 0.0
    df = pd.DataFrame({"x": list(left), "y": list(right)})
    res = pg.wilcoxon(df["x"], df["y"], alternative="two-sided")
    rbc = float(res["RBC"].iloc[0])
    if not isfinite(rbc):
        raise StatisticalProcedureError("Pingouin returned non-finite rank-biserial correlation")
    return rbc


def holm_adjust_p_values(values: Iterable[float]) -> tuple[float, ...]:
    """Apply the Holm step-down correction using Pingouin, returning adjusted values in original order."""
    p_values = tuple(float(value) for value in values)
    if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in p_values):
        raise StatisticalProcedureError("Holm correction requires finite p-values in [0, 1]")
    if len(p_values) < 2:
        return p_values
    _, adjusted = pg.multicomp(list(p_values), method="holm")
    return tuple(float(v) for v in adjusted)


def apply_holm_correction(results: Sequence[AnalysisResult]) -> tuple[AnalysisResult, ...]:
    """Apply Holm-Bonferroni correction across every paired-threshold analysis p-value."""
    candidates: list[tuple[int, float]] = [
        (index, result.p_value)
        for index, result in enumerate(results)
        if isinstance(result, PairedThresholdAnalysisResult) and result.p_value is not None
    ]
    if len(candidates) < 2:
        return tuple(results)
    adjusted = holm_adjust_p_values(value for _, value in candidates)
    updated = list(results)
    for (index, _), adjusted_value in zip(candidates, adjusted, strict=True):
        res = updated[index]
        if isinstance(res, PairedThresholdAnalysisResult):
            updated[index] = res.model_copy(update={"holm_adjusted_p_value": adjusted_value})
    return tuple(updated)


class StatisticalAnalysisUseCase:
    """Pure statistical analysis: BCa/percentile bootstrap, Wilcoxon, Spearman, linear regression."""

    def __init__(self, profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]) -> None:
        self._profiles = profiles

    def analyze_paired_seed_differences(
        self,
        scores_policy_a: tuple[float, ...],
        scores_policy_b: tuple[float, ...],
        metric_id: MetricId,
        policy_a_id: ThresholdPolicyId,
        policy_b_id: ThresholdPolicyId,
        statistical_profile_id: StatisticalProfileId,
        analysis_seed: Seed,
    ) -> PairedSeedDifferenceRecord:
        profile = self._profiles.get(statistical_profile_id)
        if (
            profile.method not in {BootstrapMethod.BCA_BOOTSTRAP, BootstrapMethod.PERCENTILE_BOOTSTRAP}
            or profile.resample_count is None
            or profile.confidence_level is None
        ):
            raise StatisticalProcedureError(
                f"Statistical profile '{statistical_profile_id.value}' is not an executable bootstrap profile"
            )
        arr_a = np.array(scores_policy_a, dtype=np.float64)
        arr_b = np.array(scores_policy_b, dtype=np.float64)
        if arr_a.shape != arr_b.shape:
            raise StatisticalProcedureError("Paired seed analysis requires equally sized policy score cohorts")
        diffs = arr_a - arr_b
        mean_diff = float(np.mean(diffs))

        method_enum = (
            ConfidenceIntervalMethod.BCA_BOOTSTRAP
            if profile.method == BootstrapMethod.BCA_BOOTSTRAP
            else ConfidenceIntervalMethod.PERCENTILE_BOOTSTRAP
        )
        ci = self._compute_bca_bootstrap_ci(
            diffs,
            resample_count=profile.resample_count.value,
            confidence_level=profile.confidence_level.value,
            analysis_seed=analysis_seed.value,
            method=method_enum,
        )
        test_res = self._compute_wilcoxon_signed_rank(arr_a, arr_b) if len(arr_a) >= 5 else None

        return PairedSeedDifferenceRecord(
            metric_id=metric_id,
            policy_a_id=policy_a_id,
            policy_b_id=policy_b_id,
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
            raise StatisticalProcedureError("Association analysis requires at least three paired finite observations")
        if not np.isfinite(predictor_values).all() or not np.isfinite(outcome_values).all():
            raise StatisticalProcedureError("Association analysis requires finite observations")
        return (
            spearman_correlation(predictor_values, outcome_values),
            simple_linear_regression(predictor_values, outcome_values),
        )

    @staticmethod
    def _compute_wilcoxon_signed_rank(x: np.ndarray, y: np.ndarray) -> HypothesisTestResult:
        differences = x - y
        nonzero = differences[np.abs(differences) > 0.0]
        if len(nonzero) == 0:
            return HypothesisTestResult(
                test_name=HypothesisTestName.WILCOXON_SIGNED_RANK,
                statistic=0.0,
                p_value=1.0,
                alternative=AlternativeHypothesis.TWO_SIDED,
            )
        df = pd.DataFrame({"x": x, "y": y})
        res = pg.wilcoxon(df["x"], df["y"], alternative="two-sided")
        return HypothesisTestResult(
            test_name=HypothesisTestName.WILCOXON_SIGNED_RANK,
            statistic=float(res["W-val"].iloc[0]),
            p_value=float(res["p-val"].iloc[0]),
            alternative=AlternativeHypothesis.TWO_SIDED,
        )

    @staticmethod
    def _compute_bca_bootstrap_ci(
        data: np.ndarray,
        resample_count: int,
        confidence_level: float,
        analysis_seed: int,
        method: ConfidenceIntervalMethod,
    ) -> ConfidenceInterval:
        if not np.isfinite(data).all():
            raise StatisticalProcedureError("Bootstrap requires finite paired seed differences")
        if math.isclose(float(np.ptp(data)), 0.0, abs_tol=0.0):
            return ConfidenceInterval(
                lower_bound=float(np.mean(data)),
                upper_bound=float(np.mean(data)),
                confidence_level=Probability(confidence_level),
                method=method,
            )
        if method == ConfidenceIntervalMethod.BCA_BOOTSTRAP and len(data) < 10:
            raise StatisticalProcedureError("BCa requires at least ten valid paired seed differences")
        if method == ConfidenceIntervalMethod.PERCENTILE_BOOTSTRAP and len(data) < 2:
            raise StatisticalProcedureError("Percentile bootstrap requires at least two valid paired seed differences")

        try:
            res = stats.bootstrap(
                (data,),
                np.mean,
                n_resamples=resample_count,
                confidence_level=confidence_level,
                method="BCa" if method == ConfidenceIntervalMethod.BCA_BOOTSTRAP else "percentile",
                rng=np.random.default_rng(analysis_seed),
            )
        except (ValueError, RuntimeError) as exc:
            raise StatisticalProcedureError(f"Bootstrap failed: {exc}") from exc
        if not np.isfinite((res.confidence_interval.low, res.confidence_interval.high)).all():
            raise StatisticalProcedureError("Bootstrap produced a non-finite confidence interval")
        return ConfidenceInterval(
            lower_bound=float(res.confidence_interval.low),
            upper_bound=float(res.confidence_interval.high),
            confidence_level=Probability(confidence_level),
            method=method,
        )
