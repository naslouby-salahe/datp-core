from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT, CONFIRMATORY_INFERENCE_PROTOCOL


def test_confirmatory_statistics_are_locked() -> None:
    assert CONFIRMATORY_INFERENCE_PROTOCOL.confidence_level.value == 0.95
    assert CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count == CONFIRMATORY_SEED_COHORT.member_count
    assert BOOTSTRAP_REPLICATE_COUNT.value == 10_000
