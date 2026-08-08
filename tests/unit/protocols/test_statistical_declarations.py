from datp_core.core.identifiers import EffectSizeId, IntervalMethod, MultiplicityCorrectionId, StatisticalTestId
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


def test_confirmatory_statistics_are_one_complete_locked_protocol() -> None:
    protocol = CONFIRMATORY_INFERENCE_PROTOCOL
    assert protocol.confidence_level.value == 0.95
    assert protocol.paired_seed_count == CONFIRMATORY_SEED_COHORT.member_count
    assert protocol.bootstrap_replicates.value == 10_000
    assert protocol.interval_method is IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN
    assert protocol.statistical_test is StatisticalTestId.WILCOXON_SIGNED_RANK
    assert protocol.wilcoxon_alternative == "two-sided"
    assert protocol.wilcoxon_zero_method == "pratt"
    assert protocol.wilcoxon_computation_preference == "exact_preferred"
    assert protocol.effect_size is EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL
    assert protocol.multiplicity_correction is MultiplicityCorrectionId.HOLM
    assert (protocol.descriptive_lower_quantile.value, protocol.descriptive_upper_quantile.value) == (0.25, 0.75)
