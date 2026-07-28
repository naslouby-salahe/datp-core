from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT, CONFIDENCE_LEVEL, PAIRED_SEED_COUNT


def test_confirmatory_statistics_are_locked() -> None:
    assert CONFIDENCE_LEVEL.value == 0.95
    assert PAIRED_SEED_COUNT.value == 10
    assert BOOTSTRAP_REPLICATE_COUNT.value == 10_000
