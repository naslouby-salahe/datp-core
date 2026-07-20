"""Application use case for statistical hypothesis testing and BCa confidence intervals."""

from __future__ import annotations

import numpy as np

from datp_core.domain.statistics import PairedSeedDifferenceRecord
from datp_core.infrastructure.statistics.scipy_adapter import compute_bca_bootstrap_ci, compute_wilcoxon_signed_rank


class StatisticalAnalysisUseCase:
    """Application use case for statistical analysis."""

    def analyze_paired_seed_differences(
        self,
        scores_policy_a: tuple[float, ...],
        scores_policy_b: tuple[float, ...],
        metric_name: str,
        policy_a_name: str,
        policy_b_name: str,
        resample_count: int = 1000,
    ) -> PairedSeedDifferenceRecord:
        arr_a = np.array(scores_policy_a, dtype=np.float64)
        arr_b = np.array(scores_policy_b, dtype=np.float64)
        diffs = arr_a - arr_b

        mean_diff = float(np.mean(diffs))
        ci = compute_bca_bootstrap_ci(diffs, resample_count=resample_count, confidence_level=0.95)
        test_res = compute_wilcoxon_signed_rank(arr_a, arr_b) if len(arr_a) >= 5 else None

        return PairedSeedDifferenceRecord(
            metric_name=metric_name,
            policy_a=policy_a_name,
            policy_b=policy_b_name,
            mean_difference=mean_diff,
            confidence_interval=ci,
            hypothesis_test=test_res,
            resample_count=resample_count,
        )
