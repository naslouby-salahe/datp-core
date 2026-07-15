import pytest

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.mathematics.effect_sizes import cliffs_delta


def test_cliffs_delta_handles_disjoint_identical_and_tied_samples() -> None:
    assert cliffs_delta(sample_a=(2.0, 3.0), sample_b=(0.0, 1.0)) == 1.0
    assert cliffs_delta(sample_a=(0.0, 1.0), sample_b=(2.0, 3.0)) == -1.0
    assert cliffs_delta(sample_a=(1.0, 2.0), sample_b=(1.0, 2.0)) == 0.0
    assert cliffs_delta(sample_a=(1.0, 2.0), sample_b=(1.0, 3.0)) == -0.25


def test_cliffs_delta_rejects_nonfinite_and_empty_samples() -> None:
    with pytest.raises(DomainValidationError):
        cliffs_delta(sample_a=(), sample_b=(1.0,))
    with pytest.raises(DomainValidationError):
        cliffs_delta(sample_a=(float("nan"),), sample_b=(1.0,))
