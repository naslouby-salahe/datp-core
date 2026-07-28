from datp_core.protocols.seeds import CONFIRMATORY_PAIRED_SEED_COUNT, CONFIRMATORY_SEED_COHORT


def test_seed_values_are_pre_registered() -> None:
    assert CONFIRMATORY_PAIRED_SEED_COUNT.value == 10
    assert CONFIRMATORY_SEED_COHORT.values == tuple(range(10))
