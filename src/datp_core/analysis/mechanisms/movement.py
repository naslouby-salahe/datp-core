"""Per-client threshold and operating-point movement evidence."""

from typing import ClassVar

from pydantic import model_validator

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue, Ratio, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate


class ThresholdOperatingPoint(StrictModel):
    threshold: ThresholdValue
    fpr: Ratio
    tpr: Ratio | None
    balanced_accuracy: Ratio | None = None
    macro_f1: Ratio | None = None


class ThresholdMovement(StrictModel):
    client: ClientIdentity
    population: PopulationId
    seed: Seed
    experiment: ExperimentId
    coordinate: FederatedTrainingCoordinate
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    shared: ThresholdOperatingPoint
    local: ThresholdOperatingPoint
    delta_threshold: MetricValue
    delta_fpr: MetricValue
    delta_tpr: MetricValue | None
    delta_balanced_accuracy: MetricValue | None
    delta_macro_f1: MetricValue | None
    score_checksum: Checksum | None = None
    evaluation_checksum: Checksum | None = None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_movement(self) -> "ThresholdMovement":
        if self.left_method is self.right_method:
            raise ValueError("threshold movement requires distinct threshold methods")
        if self.population is not self.coordinate.population:
            raise ValueError("threshold movement population must match the training coordinate")
        if self.seed != self.coordinate.training_seed:
            raise ValueError("threshold movement seed must match the training coordinate")
        return self

    @property
    def attack_availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.delta_tpr is not None else AvailabilityStatus.UNAVAILABLE

    @property
    def reason(self) -> str | None:
        return None if self.delta_tpr is not None else "attack-sensitive movement unavailable"


class ThresholdMovementCohort(StrictModel):
    movements: tuple[ThresholdMovement, ...]
    mean_delta_threshold: MetricValue | None
    mean_delta_fpr: MetricValue | None
    seed_uncertainty_delta_fpr: MetricValue | None
    availability: AvailabilityStatus
    reason: str | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_cohort(self) -> "ThresholdMovementCohort":
        if self.availability is AvailabilityStatus.AVAILABLE:
            if not self.movements or self.reason is not None:
                raise ValueError("available threshold-movement cohort requires movements and no reason")
        elif self.reason is None:
            raise ValueError("unavailable threshold-movement cohort requires an explicit reason")
        return self


def threshold_movement(
    *,
    client: ClientIdentity,
    shared: ThresholdOperatingPoint,
    local: ThresholdOperatingPoint,
    experiment: ExperimentId,
    coordinate: FederatedTrainingCoordinate,
    methods: tuple[FederatedThresholdMethod, FederatedThresholdMethod] = (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ),
    score_checksum: Checksum | None = None,
    evaluation_checksum: Checksum | None = None,
) -> ThresholdMovement:
    if (shared.tpr is None) != (local.tpr is None):
        raise ValueError("TPR movement requires both operating points or neither")
    if (shared.balanced_accuracy is None) != (local.balanced_accuracy is None):
        raise ValueError("balanced-accuracy movement requires both operating points or neither")
    if (shared.macro_f1 is None) != (local.macro_f1 is None):
        raise ValueError("Macro-F1 movement requires both operating points or neither")
    delta_tpr = None if shared.tpr is None or local.tpr is None else MetricValue(local.tpr.value - shared.tpr.value)
    delta_ba = (
        None
        if shared.balanced_accuracy is None or local.balanced_accuracy is None
        else MetricValue(local.balanced_accuracy.value - shared.balanced_accuracy.value)
    )
    delta_f1 = (
        None
        if shared.macro_f1 is None or local.macro_f1 is None
        else MetricValue(local.macro_f1.value - shared.macro_f1.value)
    )
    left_method, right_method = methods
    return ThresholdMovement(
        client=client,
        population=coordinate.population,
        seed=coordinate.training_seed,
        experiment=experiment,
        coordinate=coordinate,
        left_method=left_method,
        right_method=right_method,
        shared=shared,
        local=local,
        delta_threshold=MetricValue(local.threshold.value - shared.threshold.value),
        delta_fpr=MetricValue(local.fpr.value - shared.fpr.value),
        delta_tpr=delta_tpr,
        delta_balanced_accuracy=delta_ba,
        delta_macro_f1=delta_f1,
        score_checksum=score_checksum,
        evaluation_checksum=evaluation_checksum,
    )


def summarize_threshold_movements(
    movements: tuple[ThresholdMovement, ...],
) -> ThresholdMovementCohort:
    if not movements:
        return ThresholdMovementCohort(
            movements=(),
            mean_delta_threshold=None,
            mean_delta_fpr=None,
            seed_uncertainty_delta_fpr=None,
            availability=AvailabilityStatus.UNAVAILABLE,
            reason="no threshold-movement observations",
        )
    delta_thresholds = tuple(item.delta_threshold.value for item in movements)
    delta_fprs = tuple(item.delta_fpr.value for item in movements)
    mean_fpr = sum(delta_fprs) / len(delta_fprs)
    variance = sum((value - mean_fpr) ** 2 for value in delta_fprs) / len(delta_fprs)
    return ThresholdMovementCohort(
        movements=movements,
        mean_delta_threshold=MetricValue(sum(delta_thresholds) / len(delta_thresholds)),
        mean_delta_fpr=MetricValue(mean_fpr),
        seed_uncertainty_delta_fpr=MetricValue(variance**0.5),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )
