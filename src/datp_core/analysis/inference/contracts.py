from enum import StrEnum

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EffectSizeId,
    IntervalMethod,
    MultiplicityCorrectionId,
    StatisticalTestId,
)
from datp_core.core.numeric import BootstrapReplicateCount, ConfidenceLevel, Ratio, SeedCount


class WilcoxonAlternative(StrEnum):
    TWO_SIDED = "two-sided"


class WilcoxonZeroMethod(StrEnum):
    PRATT = "pratt"


class WilcoxonComputationPreference(StrEnum):
    EXACT_PREFERRED = "exact_preferred"


class PairedInferenceProtocol(StrictModel):
    confidence_level: ConfidenceLevel
    paired_seed_count: SeedCount
    interval_method: IntervalMethod
    bootstrap_replicates: BootstrapReplicateCount
    statistical_test: StatisticalTestId
    wilcoxon_alternative: WilcoxonAlternative
    wilcoxon_zero_method: WilcoxonZeroMethod
    wilcoxon_computation_preference: WilcoxonComputationPreference
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
        if self.wilcoxon_computation_preference is not WilcoxonComputationPreference.EXACT_PREFERRED:
            raise ValueError("paired Wilcoxon must prefer exact computation when feasible")
        if self.descriptive_lower_quantile > self.descriptive_upper_quantile:
            raise ValueError("descriptive lower quantile cannot exceed the upper quantile")
        return self
