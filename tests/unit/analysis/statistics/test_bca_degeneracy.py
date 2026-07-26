"""The confirmatory BCa contract handles degenerate and edge-case inputs gracefully."""

import numpy as np
import pytest

from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.analysis.statistics.models import StatisticalProcedureError


def test_bca_rejects_fewer_than_ten_paired_seed_differences_with_variance() -> None:
    with pytest.raises(StatisticalProcedureError, match="at least ten"):
        StatisticalAnalysisUseCase._compute_bca_bootstrap_ci(
            np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]), 10_000, 0.95, 300, "bca_bootstrap"
        )


def test_bca_returns_degenerate_ci_for_identical_paired_seed_differences() -> None:
    result = StatisticalAnalysisUseCase._compute_bca_bootstrap_ci(np.full(10, 0.1), 10_000, 0.95, 300, "bca_bootstrap")
    assert result.lower_bound == 0.1
    assert result.upper_bound == 0.1


def test_bca_single_value_is_valid_degenerate_ci() -> None:
    result = StatisticalAnalysisUseCase._compute_bca_bootstrap_ci(np.array([0.1]), 10_000, 0.95, 300, "bca_bootstrap")
    assert result.lower_bound == 0.1
    assert result.upper_bound == 0.1
