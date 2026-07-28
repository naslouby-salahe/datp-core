"""Confirmatory inference declarations."""

from datp_core.domain.enums import EffectSizeId, IntervalMethod, MultiplicityCorrectionId, StatisticalTestId
from datp_core.domain.values import BootstrapReplicateCount, ConfidenceLevel

from .models import StatisticalInferenceProtocol
from .seeds import CONFIRMATORY_SEED_COHORT

CONFIRMATORY_INFERENCE_PROTOCOL = StatisticalInferenceProtocol(
    confidence_level=ConfidenceLevel(0.95),
    seed_cohort=CONFIRMATORY_SEED_COHORT,
)
CONFIRMATORY_INTERVAL_METHOD = IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN
SECONDARY_TEST = StatisticalTestId.WILCOXON_SIGNED_RANK
SECONDARY_EFFECT_SIZE = EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL
SECONDARY_MULTIPLICITY = MultiplicityCorrectionId.HOLM
BOOTSTRAP_REPLICATE_COUNT = BootstrapReplicateCount(10_000)
