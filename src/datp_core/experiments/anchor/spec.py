"""Historical DATP anchor specification and reference decision protocol."""

from typing import Literal

from pydantic import model_validator

from datp_core.analysis.metrics.contracts import OPERATING_POINT_METRICS
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    AbsoluteTolerance,
    MetricValue,
    Seed,
)
from datp_core.experiments.common.coordinates import ExperimentSpec
from datp_core.experiments.common.seeds import SeedCohort

ANCHOR_EXPERIMENT = ExperimentSpec(
    id=ExperimentId.HISTORICAL_DATP_REPRODUCTION,
    role=EvidenceRole.ANCHOR_REPRODUCTION,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ),
    metrics=OPERATING_POINT_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)


class AnchorReference(StrictModel):
    seed: Seed
    threshold_method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ]
    metric: MetricId
    value: MetricValue
    absolute_tolerance: AbsoluteTolerance | MetricValue


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
            absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
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
            absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
        )
        for seed, value in zip(
            HISTORICAL_ANCHOR_SEED_COHORT.values,
            HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
            strict=True,
        )
    ),
)
