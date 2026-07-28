import pytest

from datp_core.domain.values import MetricValue, Quantile, Ratio, Seed


def test_value_boundaries_and_immutability() -> None:
    assert Ratio(0).value == 0
    assert Ratio(1).value == 1
    assert MetricValue(2).value == 2
    with pytest.raises(ValueError):
        Quantile(1)
    with pytest.raises(ValueError):
        Seed(True)
    assert hash(Ratio(0.5)) == hash(Ratio(0.5))
