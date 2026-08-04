from tests.unit.analysis.inference.test_bootstrap import contrasts

from datp_core.analysis.inference.paired import holm_adjust, matched_pairs_rank_biserial, paired_wilcoxon
from datp_core.analysis.models import MultiplicityPlan, PValue
from datp_core.domain.enums import AvailabilityStatus
from datp_core.domain.values import Ratio
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL


def test_paired_inference_uses_the_declared_protocol() -> None:
    values = contrasts()
    wilcoxon = paired_wilcoxon(values, CONFIRMATORY_INFERENCE_PROTOCOL)
    effect = matched_pairs_rank_biserial(values, CONFIRMATORY_INFERENCE_PROTOCOL)
    assert wilcoxon.availability is AvailabilityStatus.AVAILABLE
    assert wilcoxon.computation_method is not None
    assert wilcoxon.computation_method.value == CONFIRMATORY_INFERENCE_PROTOCOL.wilcoxon_computation_method
    assert effect.availability is AvailabilityStatus.AVAILABLE
    assert effect.value is not None and -1.0 <= effect.value.value <= 1.0


def test_multiplicity_uses_a_complete_typed_plan() -> None:
    result = holm_adjust(
        MultiplicityPlan(
            family_name="predeclared_supportive_family",
            raw_p_values=(PValue(0.01), PValue(0.04)),
            alpha=Ratio(0.05),
        ),
        CONFIRMATORY_INFERENCE_PROTOCOL,
    )
    assert result.correction is CONFIRMATORY_INFERENCE_PROTOCOL.multiplicity_correction
    assert result.raw_p_values == (PValue(0.01), PValue(0.04))
    assert result.adjusted_p_values[0].value <= result.adjusted_p_values[1].value
