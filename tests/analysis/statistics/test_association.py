"""Unit tests for pure association primitives."""

from __future__ import annotations

import numpy as np
import pytest

from datp_core.analysis.enums import AlternativeHypothesis, HypothesisTestName
from datp_core.analysis.statistics.association import simple_linear_regression, spearman_correlation


def test_spearman_correlation_typed() -> None:
    predictor = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    outcome = np.array([2.0, 4.0, 6.0, 8.0, 10.0], dtype=np.float64)

    res = spearman_correlation(predictor, outcome)
    assert res.test_name == HypothesisTestName.SPEARMAN_CORRELATION
    assert isinstance(res.test_name, HypothesisTestName)
    assert res.alternative == AlternativeHypothesis.TWO_SIDED
    assert res.statistic == pytest.approx(1.0)


def test_simple_linear_regression() -> None:
    predictor = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    outcome = np.array([2.0, 4.0, 6.0, 8.0, 10.0], dtype=np.float64)

    reg = simple_linear_regression(predictor, outcome)
    assert reg.slope == 2.0
    assert reg.intercept == 0.0
    assert reg.r_squared == 1.0
    assert len(reg.leverage) == 5
