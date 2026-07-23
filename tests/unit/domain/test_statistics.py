"""Pure matched-pair statistical procedures retain their pre-registered semantics."""

import pytest

from datp_core.analysis.models import (
    StatisticalProcedureError,
    holm_adjust_p_values,
    matched_pairs_rank_biserial_correlation,
)


def test_rank_biserial_uses_signed_average_ranks_and_excludes_zero_differences() -> None:
    assert matched_pairs_rank_biserial_correlation((3.0, 5.0, 2.0, 4.0), (2.0, 7.0, 2.0, 1.0)) == pytest.approx(
        1.0 / 3.0
    )

    with pytest.raises(StatisticalProcedureError, match="all paired differences are zero"):
        matched_pairs_rank_biserial_correlation((1.0,), (1.0,))


def test_holm_adjustment_is_step_down_monotonic_and_preserves_input_order() -> None:
    assert holm_adjust_p_values((0.03, 0.01, 0.04)) == pytest.approx((0.06, 0.03, 0.06))
