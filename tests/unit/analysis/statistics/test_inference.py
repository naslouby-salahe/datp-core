"""The matched-pairs rank-biserial effect size retains its pre-registered semantics."""

import pytest

from datp_core.analysis.statistics.inference import matched_pairs_rank_biserial_correlation


def test_rank_biserial_uses_signed_average_ranks_and_excludes_zero_differences() -> None:
    assert matched_pairs_rank_biserial_correlation((3.0, 5.0, 2.0, 4.0), (2.0, 7.0, 2.0, 1.0)) == pytest.approx(
        1.0 / 3.0
    )


def test_rank_biserial_returns_zero_when_all_differences_are_zero() -> None:
    assert matched_pairs_rank_biserial_correlation((1.0,), (1.0,)) == 0.0
    assert matched_pairs_rank_biserial_correlation((1.0, 2.0, 3.0), (1.0, 2.0, 3.0)) == 0.0
