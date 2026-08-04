"""Complete paired-inference declarations."""

from pydantic import model_validator

from datp_core.domain.enums import (
    EffectSizeId,
    IntervalMethod,
    MultiplicityCorrectionId,
    StatisticalTestId,
)
from datp_core.domain.values import BootstrapReplicateCount, ConfidenceLevel, Ratio

from .models import StatisticalInferenceProtocol
from .seeds import CONFIRMATORY_SEED_COHORT


class PairedInferenceProtocol(StatisticalInferenceProtocol):
    """Single source of truth for every paired-analysis numerical and procedural choice."""

    interval_method: IntervalMethod
    bootstrap_replicates: BootstrapReplicateCount
    statistical_test: StatisticalTestId
    wilcoxon_alternative: str
    wilcoxon_zero_method: str
    wilcoxon_computation_method: str
    effect_size: EffectSizeId
    multiplicity_correction: MultiplicityCorrectionId
    descriptive_lower_quantile: Ratio
    descriptive_upper_quantile: Ratio

    @model_validator(mode="after")
    def validate_protocol(self) -> "PairedInferenceProtocol":
        if self.wilcoxon_alternative != "two-sided":
            raise ValueError("paired Wilcoxon alternative must remain two-sided")
        if self.wilcoxon_zero_method != "pratt":
            raise ValueError("paired Wilcoxon zero handling must remain Pratt")
        if self.wilcoxon_computation_method != "asymptotic":
            raise ValueError("paired Wilcoxon computation must remain asymptotic")
        if self.descriptive_lower_quantile > self.descriptive_upper_quantile:
            raise ValueError("descriptive lower quantile cannot exceed the upper quantile")
        return self


CONFIRMATORY_INFERENCE_PROTOCOL = PairedInferenceProtocol(
    confidence_level=ConfidenceLevel(0.95),
    seed_cohort=CONFIRMATORY_SEED_COHORT,
    interval_method=IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
    bootstrap_replicates=BootstrapReplicateCount(10_000),
    statistical_test=StatisticalTestId.WILCOXON_SIGNED_RANK,
    wilcoxon_alternative="two-sided",
    wilcoxon_zero_method="pratt",
    wilcoxon_computation_method="asymptotic",
    effect_size=EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL,
    multiplicity_correction=MultiplicityCorrectionId.HOLM,
    descriptive_lower_quantile=Ratio(0.25),
    descriptive_upper_quantile=Ratio(0.75),
)

CONFIRMATORY_INTERVAL_METHOD = CONFIRMATORY_INFERENCE_PROTOCOL.interval_method
SECONDARY_TEST = CONFIRMATORY_INFERENCE_PROTOCOL.statistical_test
SECONDARY_EFFECT_SIZE = CONFIRMATORY_INFERENCE_PROTOCOL.effect_size
SECONDARY_MULTIPLICITY = CONFIRMATORY_INFERENCE_PROTOCOL.multiplicity_correction
BOOTSTRAP_REPLICATE_COUNT = CONFIRMATORY_INFERENCE_PROTOCOL.bootstrap_replicates
