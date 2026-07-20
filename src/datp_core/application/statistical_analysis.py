"""Application use case for statistical hypothesis testing and BCa confidence intervals."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from datp_core.domain.catalogue import StatisticalProfileRecord
from datp_core.domain.identifiers import MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.domain.statistics import ConfidenceInterval, HypothesisTestResult, PairedSeedDifferenceRecord
from datp_core.domain.values import Seed, TypedDomainRegistry


class StatisticalAnalysisPort(Protocol):
    def bootstrap_ci(
        self,
        data: np.ndarray,
        resample_count: int,
        confidence_level: float,
        analysis_seed: int,
    ) -> ConfidenceInterval: ...

    def wilcoxon(self, left: np.ndarray, right: np.ndarray) -> HypothesisTestResult: ...


class StatisticalAnalysisUseCase:
    """Application use case for statistical analysis."""

    def __init__(
        self,
        statistics: StatisticalAnalysisPort,
        profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord],
    ) -> None:
        self._statistics = statistics
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
        if profile.method != "bca_bootstrap" or profile.resample_count is None or profile.confidence_level is None:
            raise ValueError(f"Statistical profile '{statistical_profile_id.value}' is not an executable BCa profile")
        arr_a = np.array(scores_policy_a, dtype=np.float64)
        arr_b = np.array(scores_policy_b, dtype=np.float64)
        diffs = arr_a - arr_b

        mean_diff = float(np.mean(diffs))
        ci = self._statistics.bootstrap_ci(
            diffs,
            resample_count=profile.resample_count.value,
            confidence_level=profile.confidence_level.value,
            analysis_seed=analysis_seed.value,
        )
        test_res = self._statistics.wilcoxon(arr_a, arr_b) if len(arr_a) >= 5 else None

        return PairedSeedDifferenceRecord(
            metric_id=MetricId(metric_name),
            policy_a_id=ThresholdPolicyId(policy_a_name),
            policy_b_id=ThresholdPolicyId(policy_b_name),
            mean_difference=mean_diff,
            confidence_interval=ci,
            hypothesis_test=test_res,
            resample_count=profile.resample_count.value,
            analysis_seed=analysis_seed,
        )
