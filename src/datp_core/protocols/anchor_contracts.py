"""Confirmatory endpoint and historical anchor protocol contracts."""

from typing import Literal

from pydantic import model_validator

from datp_core.domain.enums import (
    ConfirmatoryDeltaDirection,
    ExperimentId,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values import (
    AbsoluteTolerance,
    ConfidenceLevel,
    MetricValue,
    Seed,
    SeedCount,
)
from datp_core.protocols.models import Declaration, SeedCohort

CONFIRMATORY_PAIRED_SEED_COUNT = SeedCount(10)


class ConfirmatoryEndpoint(Declaration):
    experiment: Literal[ExperimentId.SHARED_VS_LOCAL_CONFIRMATION]
    population: Literal[PopulationId.NBAIOT_NATURAL_DEVICES]
    training_model: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    shared_threshold: Literal[FederatedThresholdMethod.SHARED_THRESHOLD]
    local_threshold: Literal[FederatedThresholdMethod.LOCAL_THRESHOLD]
    metric: Literal[MetricId.FPR_COEFFICIENT_OF_VARIATION]
    seed_cohort: SeedCohort
    positive_direction: Literal[ConfirmatoryDeltaDirection.SHARED_MINUS_LOCAL]
    interval_method: Literal[IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN]
    confidence_level: ConfidenceLevel

    @model_validator(mode="after")
    def validate_endpoint(self) -> "ConfirmatoryEndpoint":
        if self.seed_cohort.member_count != CONFIRMATORY_PAIRED_SEED_COUNT:
            raise ValueError("confirmatory endpoint requires the paired ten-seed journal cohort")
        if MetricId.AUROC is self.metric:
            raise ValueError("AUROC is a model-quality control, not the confirmatory endpoint")
        return self


class AnchorReference(Declaration):
    seed: Seed
    threshold_method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ]
    metric: MetricId
    value: MetricValue
    absolute_tolerance: AbsoluteTolerance | MetricValue


class AnchorDecisionProtocol(Declaration):
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
        if len(set(coordinates)) != len(coordinates):
            raise ValueError("anchor references must be unique by seed, threshold method, and metric")
        return self
