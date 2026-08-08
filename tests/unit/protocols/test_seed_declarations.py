from datp_core.experiments.common.seeds import (
    BOUNDED_EVIDENCE_SEED_COHORT,
    CONFIRMATORY_ANALYSIS_SEED,
    CONFIRMATORY_SEED_COHORT,
)
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


def test_seed_values_are_pre_registered() -> None:
    assert CONFIRMATORY_SEED_COHORT == CONFIRMATORY_INFERENCE_PROTOCOL.seed_cohort
    assert tuple(seed.value for seed in CONFIRMATORY_SEED_COHORT.values) == tuple(
        range(CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count.value)
    )
    assert tuple(seed.value for seed in BOUNDED_EVIDENCE_SEED_COHORT.values) == tuple(range(10))
    assert CONFIRMATORY_ANALYSIS_SEED.value == 31
