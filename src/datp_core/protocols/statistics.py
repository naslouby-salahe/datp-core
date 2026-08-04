"""Complete paired-inference declarations."""

from enum import StrEnum

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


class WilcoxonAlternative(StrEnum):
    TWO_SIDED = "two-sided"


class WilcoxonZeroMethod(StrEnum):
    PRATT = "pratt"


class WilcoxonComputationMethod(StrEnum):
    SCIPY_ASYMPTOTIC = "asymptotic"


class PairedInferenceProtocol(StatisticalInferenceProtocol):
    """Single source of truth for every paired-analysis numerical and procedural choice."""

    interval_method: IntervalMethod
    bootstrap_replicates: BootstrapReplicateCount
    statistical_test: StatisticalTestId
    wilcoxon_alternative: WilcoxonAlternative
    wilcoxon_zero_method: WilcoxonZeroMethod
    wilcoxon_computation_method: WilcoxonComputationMethod
    effect_size: EffectSizeId
    multiplicity_correction: MultiplicityCorrectionId
    descriptive_lower_quantile: Ratio
    descriptive_upper_quantile: Ratio

    @model_validator(mode="after")
    def validate_protocol(self) -> "PairedInferenceProtocol":
        if self.wilcoxon_alternative is not WilcoxonAlternative.TWO_SIDED:
            raise ValueError("paired Wilcoxon alternative must remain two-sided")
        if self.wilcoxon_zero_method is not WilcoxonZeroMethod.PRATT:
            raise ValueError("paired Wilcoxon zero handling must remain Pratt")
        if self.wilcoxon_computation_method is not WilcoxonComputationMethod.SCIPY_ASYMPTOTIC:
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
    wilcoxon_alternative=WilcoxonAlternative.TWO_SIDED,
    wilcoxon_zero_method=WilcoxonZeroMethod.PRATT,
    wilcoxon_computation_method=WilcoxonComputationMethod.SCIPY_ASYMPTOTIC,
    effect_size=EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL,
    multiplicity_correction=MultiplicityCorrectionId.HOLM,
    descriptive_lower_quantile=Ratio(0.25),
    descriptive_upper_quantile=Ratio(0.75),
)

BOOTSTRAP_REPLICATE_COUNT = CONFIRMATORY_INFERENCE_PROTOCOL.bootstrap_replicates
