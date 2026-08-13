from dataclasses import fields

from datp_core.analysis.preparation import ConfirmatoryAnalysisRequest
from datp_core.analysis.scientific_decision import ScientificDecision
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


def test_confirmatory_analysis_contract_has_no_seed_exclusion_path() -> None:
    assert "excluded_seeds" not in {field.name for field in fields(ConfirmatoryAnalysisRequest)}


def test_confirmatory_inference_unavailability_has_a_dedicated_state() -> None:
    assert ScientificDecision.CONFIRMATORY_INFERENCE_UNAVAILABLE.value == "confirmatory_inference_unavailable"
