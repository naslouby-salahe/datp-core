"""The confirmatory BCa contract rejects invalid inputs explicitly."""

import numpy as np
import pytest

from datp_core.analysis.models import StatisticalAnalysisUseCase
from datp_core.analysis.models import StatisticalProcedureError


def test_bca_rejects_fewer_than_ten_paired_seed_differences() -> None:
    with pytest.raises(StatisticalProcedureError, match="at least ten"):
        StatisticalAnalysisUseCase._compute_bca_bootstrap_ci(np.array([0.1]), 10_000, 0.95, 300, "bca_bootstrap")


def test_bca_rejects_identical_paired_seed_differences() -> None:
    with pytest.raises(StatisticalProcedureError, match="identical"):
        StatisticalAnalysisUseCase._compute_bca_bootstrap_ci(np.full(10, 0.1), 10_000, 0.95, 300, "bca_bootstrap")
