"""Holm-Bonferroni correction retains its pre-registered step-down semantics."""

import pytest

from datp_core.analysis.statistics.multiplicity import holm_adjust_p_values


def test_holm_adjustment_is_step_down_monotonic_and_preserves_input_order() -> None:
    assert holm_adjust_p_values((0.03, 0.01, 0.04)) == pytest.approx((0.06, 0.03, 0.06))
