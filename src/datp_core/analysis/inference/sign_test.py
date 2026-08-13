from math import comb

from pydantic import model_validator

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.inference.wilcoxon import PValue
from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import PairedObservationCount


class ExactPairedSignTestResult(StrictModel):
    positive_pair_count: PairedObservationCount
    negative_pair_count: PairedObservationCount
    nonzero_pair_count: PairedObservationCount
    two_sided_p_value: PValue | None

    @model_validator(mode="after")
    def validate_result(self) -> "ExactPairedSignTestResult":
        if self.positive_pair_count > self.nonzero_pair_count:
            raise ValueError("positive sign-test pairs cannot exceed nonzero pairs")
        if self.negative_pair_count > self.nonzero_pair_count:
            raise ValueError("negative sign-test pairs cannot exceed nonzero pairs")
        if self.positive_pair_count.value + self.negative_pair_count.value != self.nonzero_pair_count.value:
            raise ValueError("sign-test nonzero pairs must equal the positive plus negative counts")
        if (self.nonzero_pair_count.value == 0) != (self.two_sided_p_value is None):
            raise ValueError("sign-test p-value is unavailable exactly when every paired delta is zero")
        return self


def exact_paired_sign_test(contrasts: PairedContrasts) -> ExactPairedSignTestResult:
    deltas = contrasts.deltas
    positive = sum(item.value > 0.0 for item in deltas)
    negative = sum(item.value < 0.0 for item in deltas)
    nonzero = sum(item.value != 0.0 for item in deltas)
    return ExactPairedSignTestResult(
        positive_pair_count=PairedObservationCount(positive),
        negative_pair_count=PairedObservationCount(negative),
        nonzero_pair_count=PairedObservationCount(nonzero),
        two_sided_p_value=None if nonzero == 0 else PValue(_exact_two_sided_binomial_p_value(positive, nonzero)),
    )


def _exact_two_sided_binomial_p_value(positive: int, nonzero: int) -> float:
    tail = sum(comb(nonzero, index) for index in range(min(positive, nonzero - positive) + 1))
    return min(1.0, 2.0 * tail / (2**nonzero))
