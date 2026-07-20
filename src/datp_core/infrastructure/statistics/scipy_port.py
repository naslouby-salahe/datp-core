"""SciPy implementation of the application statistical-analysis port."""

from __future__ import annotations

import numpy as np

from datp_core.domain.statistics import ConfidenceInterval, HypothesisTestResult
from datp_core.infrastructure.statistics.scipy_adapter import compute_bca_bootstrap_ci, compute_wilcoxon_signed_rank


class ScipyStatisticalAnalysisAdapter:
    def bootstrap_ci(
        self,
        data: np.ndarray,
        resample_count: int,
        confidence_level: float,
        analysis_seed: int,
    ) -> ConfidenceInterval:
        return compute_bca_bootstrap_ci(
            data,
            resample_count=resample_count,
            confidence_level=confidence_level,
            analysis_seed=analysis_seed,
        )

    def wilcoxon(self, left: np.ndarray, right: np.ndarray) -> HypothesisTestResult:
        return compute_wilcoxon_signed_rank(left, right)
