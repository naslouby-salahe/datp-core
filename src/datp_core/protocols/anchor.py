"""Historical anchor declarations."""

from datp_core.domain.enums import FederatedThresholdMethod, MetricId
from datp_core.domain.values import MetricValue, Seed

from .models import AnchorDecisionProtocol, AnchorReference, SeedCohort

FIXED_SCORE_ABSOLUTE_TOLERANCE = MetricValue(1e-12)
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
            absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE,
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
            absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE,
        )
        for seed, value in zip(
            HISTORICAL_ANCHOR_SEED_COHORT.values,
            HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
            strict=True,
        )
    ),
)
