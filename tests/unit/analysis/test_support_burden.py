import pytest

from datp_core.analysis.mechanisms.support_burden import _average_ranks, _spearman


def test_support_burden_spearman_uses_average_ranks_for_ties() -> None:
    assert _average_ranks((1.0, 1.0, 3.0)) == (1.5, 1.5, 3.0)
    assert _spearman((1.0, 1.0, 3.0), (1.0, 1.0, 3.0)) == pytest.approx(1.0)


def test_support_burden_spearman_marks_constant_input_unavailable() -> None:
    assert _spearman((1.0, 1.0, 1.0), (1.0, 2.0, 3.0)) is None
