"""Historical DATP anchor specification and reference decision protocol."""

from typing import Literal

from pydantic import model_validator

from datp_core.analysis.inference.contracts import (
    PairedInferenceProtocol,
    WilcoxonAlternative,
    WilcoxonComputationPreference,
    WilcoxonZeroMethod,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EffectSizeId,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    MultiplicityCorrectionId,
    StatisticalTestId,
)
from datp_core.core.numeric import (
    BootstrapReplicateCount,
    ConfidenceLevel,
    MetricValue,
    Ratio,
    Seed,
)
from datp_core.experiments.anchor.contracts import MetricInterval
from datp_core.experiments.common.seeds import SeedCohort


class AnchorReference(StrictModel):
    """One per-seed historical CV(FPR) constant, reported as a diagnostic.

    Per-seed values are diagnostic only (see DiagnosticRule); the roadmap gate
    confirms the cohort-level BCa interval on the five-seed cohort, not any
    per-seed value equality.
    """

    seed: Seed
    threshold_method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ]
    metric: MetricId
    value: MetricValue


class AnchorDecisionProtocol(StrictModel):
    seed_cohort: SeedCohort
    references: tuple[AnchorReference, ...]

    @model_validator(mode="after")
    def validate_seed_coverage(self) -> "AnchorDecisionProtocol":
        reference_seeds = frozenset(reference.seed for reference in self.references)
        cohort_seeds = frozenset(self.seed_cohort.values)
        if reference_seeds != cohort_seeds:
            raise ValueError("anchor references must cover exactly the historical seed cohort")
        coordinates = tuple(
            (reference.seed, reference.threshold_method, reference.metric) for reference in self.references
        )
        if len(frozenset(coordinates)) != len(coordinates):
            raise ValueError("anchor references must be unique by seed, threshold method, and metric")
        return self


HISTORICAL_SHARED_THRESHOLD_CV_FPR = (
    MetricValue(1.0448312675151203),
    MetricValue(1.016550264110769),
    MetricValue(1.014596557101379),
    MetricValue(1.018182331886956),
    MetricValue(0.9919831320412626),
)
HISTORICAL_LOCAL_THRESHOLD_CV_FPR = (
    MetricValue(0.34682905931632996),
    MetricValue(0.25118527436389065),
    MetricValue(0.24251990260091283),
    MetricValue(0.2513155690288227),
    MetricValue(0.40432991985550865),
)
HISTORICAL_ANCHOR_SEED_COHORT = SeedCohort(
    values=tuple(Seed(index) for index, _ in enumerate(HISTORICAL_SHARED_THRESHOLD_CV_FPR))
)
ANCHOR_DECISION_PROTOCOL = AnchorDecisionProtocol(
    seed_cohort=HISTORICAL_ANCHOR_SEED_COHORT,
    references=tuple(
        AnchorReference(
            seed=seed,
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            value=value,
        )
        for seed, value in zip(
            HISTORICAL_ANCHOR_SEED_COHORT.values,
            HISTORICAL_SHARED_THRESHOLD_CV_FPR,
            strict=True,
        )
    )
    + tuple(
        AnchorReference(
            seed=seed,
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            value=value,
        )
        for seed, value in zip(
            HISTORICAL_ANCHOR_SEED_COHORT.values,
            HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
            strict=True,
        )
    ),
)

ANCHOR_REFERENCE_INTERVAL = MetricInterval(lower=MetricValue(0.647), upper=MetricValue(0.769))
ANCHOR_REFERENCE_INTERVAL_WIDTH = MetricValue(0.122)
ANCHOR_MAXIMUM_WIDTH_MULTIPLIER = MetricValue(1.20)
ANCHOR_MAXIMUM_OPERATIVE_WIDTH = MetricValue(
    ANCHOR_REFERENCE_INTERVAL_WIDTH.value * ANCHOR_MAXIMUM_WIDTH_MULTIPLIER.value
)

ANCHOR_INFERENCE_PROTOCOL = PairedInferenceProtocol(
    confidence_level=ConfidenceLevel(0.95),
    paired_seed_count=HISTORICAL_ANCHOR_SEED_COHORT.member_count,
    interval_method=IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
    bootstrap_replicates=BootstrapReplicateCount(10_000),
    statistical_test=StatisticalTestId.WILCOXON_SIGNED_RANK,
    wilcoxon_alternative=WilcoxonAlternative.TWO_SIDED,
    wilcoxon_zero_method=WilcoxonZeroMethod.PRATT,
    wilcoxon_computation_preference=WilcoxonComputationPreference.EXACT_PREFERRED,
    effect_size=EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL,
    multiplicity_correction=MultiplicityCorrectionId.HOLM,
    descriptive_lower_quantile=Ratio(0.25),
    descriptive_upper_quantile=Ratio(0.75),
)
