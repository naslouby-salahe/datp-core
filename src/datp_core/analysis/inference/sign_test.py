from math import comb

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.inference.wilcoxon import PValue
from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import PairedObservationCount


class ExactPairedSignTestResult(StrictModel):
    positive_pair_count: PairedObservationCount
    nonzero_pair_count: PairedObservationCount
    two_sided_p_value: PValue | None


def exact_paired_sign_test(contrasts: PairedContrasts) -> ExactPairedSignTestResult:
    deltas = contrasts.deltas
    positive = sum(item.value > 0.0 for item in deltas)
    nonzero = sum(item.value != 0.0 for item in deltas)
    return ExactPairedSignTestResult(
        positive_pair_count=PairedObservationCount(positive),
        nonzero_pair_count=PairedObservationCount(nonzero),
        two_sided_p_value=None if nonzero == 0 else PValue(_exact_two_sided_binomial_p_value(positive, nonzero)),
    )


def _exact_two_sided_binomial_p_value(positive: int, nonzero: int) -> float:
    tail = sum(comb(nonzero, index) for index in range(min(positive, nonzero - positive) + 1))
    return min(1.0, 2.0 * tail / (2**nonzero))
