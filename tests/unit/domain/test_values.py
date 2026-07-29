import pytest

from datp_core.domain.values import ClientCount, MetricValue, Quantile, Ratio, Seed, SeedCount
from datp_core.protocols.models import SeedCohort
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL


def test_value_boundaries_and_immutability() -> None:
    assert Ratio(0).value == 0
    assert Ratio(1).value == 1
    assert MetricValue(2).value == 2
    with pytest.raises(ValueError):
        Quantile(1)
    with pytest.raises(ValueError):
        Seed(True)
    assert hash(Ratio(0.5)) == hash(Ratio(0.5))


def test_seed_count_is_not_client_count() -> None:
    seed_count = SeedCount(10)
    client_count = ClientCount(10)
    assert seed_count == SeedCount(10)
    assert seed_count != client_count
    assert CONFIRMATORY_SEED_COHORT.member_count == SeedCount(10)
    assert isinstance(CONFIRMATORY_SEED_COHORT.member_count, SeedCount)
    assert not isinstance(CONFIRMATORY_SEED_COHORT.member_count, ClientCount)
    assert CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count == SeedCount(10)
    assert isinstance(CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count, SeedCount)
    cohort = SeedCohort(values=(Seed(0), Seed(1)))
    assert cohort.member_count == SeedCount(2)
