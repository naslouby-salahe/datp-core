"""Threshold-estimation diagnostics against an exact pooled benign reference."""

from dataclasses import dataclass
from itertools import groupby

import numpy as np

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import MetricId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, Seed, SubsampleReplicateCount
from datp_core.domain.values.ratios import Quantile, Ratio, ThresholdValue, ThresholdVariance
from datp_core.evaluation.metric_semantics import available, metric_value, unavailable
from datp_core.evaluation.models import (
    MetricAvailability,
    MetricReason,
    MetricStatus,
    metric_by_id,
    validate_metric_set,
)
from datp_core.evaluation.threshold_evidence import VerifiedHeldOutBenignScores
from datp_core.learning.federated.models import FederatedTrainingCoordinate

_THRESHOLD_ESTIMATION_METRICS = frozenset(
    {
        MetricId.ABSOLUTE_THRESHOLD_ERROR,
        MetricId.RELATIVE_THRESHOLD_ERROR,
        MetricId.SIGNED_ATTAINMENT_ERROR,
        MetricId.ABSOLUTE_ATTAINMENT_ERROR,
    }
)


@dataclass(frozen=True, slots=True)
class ThresholdEstimationProvenance:
    """Immutable coordinate and calibration identity for one threshold estimate."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    calibration_size: CalibrationSize
    replicate_index: ReplicateIndex
    quantile: Quantile

    def __post_init__(self) -> None:
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("threshold-estimation coordinate must match client and training seed")


@dataclass(frozen=True, slots=True)
class ThresholdEstimationDiagnostic:
    """One threshold estimate assessed only with verified benign score evidence."""

    provenance: ThresholdEstimationProvenance
    estimated_threshold: ThresholdValue
    exact_pooled_benign_quantile_reference: ThresholdValue
    target_exceedance: Ratio
    achieved_benign_exceedance: Ratio
    metrics: tuple[MetricAvailability, ...]

    def __post_init__(self) -> None:
        validate_metric_set(self.metrics, _THRESHOLD_ESTIMATION_METRICS)
        absolute_threshold = metric_by_id(self.metrics, MetricId.ABSOLUTE_THRESHOLD_ERROR)
        relative_threshold = metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR)
        signed_attainment = metric_by_id(self.metrics, MetricId.SIGNED_ATTAINMENT_ERROR)
        absolute_attainment = metric_by_id(self.metrics, MetricId.ABSOLUTE_ATTAINMENT_ERROR)
        if absolute_threshold.value is None or signed_attainment.value is None or absolute_attainment.value is None:
            raise ScientificContractError("absolute and attainment threshold diagnostics must be available")
        if absolute_threshold.value.value < 0 or absolute_attainment.value.value < 0:
            raise ScientificContractError("absolute threshold diagnostics must be non-negative")
        if relative_threshold.value is None and relative_threshold.reason is not MetricReason.ZERO_MEAN:
            raise ScientificContractError("undefined relative threshold error requires a zero-reference reason")
        expected_signed = self.achieved_benign_exceedance.value - self.target_exceedance.value
        if signed_attainment.value.value != expected_signed:
            raise ScientificContractError("signed attainment error must match achieved minus target exceedance")

    @property
    def absolute_threshold_error(self) -> float:
        value = metric_value(metric_by_id(self.metrics, MetricId.ABSOLUTE_THRESHOLD_ERROR))
        if value is None:
            raise RuntimeError("absolute threshold error is required")
        return value

    @property
    def relative_threshold_error_status(self) -> MetricStatus:
        return metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR).status

    @property
    def relative_threshold_error(self) -> float | None:
        return metric_value(metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR))

    @property
    def signed_attainment_error(self) -> float:
        value = metric_value(metric_by_id(self.metrics, MetricId.SIGNED_ATTAINMENT_ERROR))
        if value is None:
            raise RuntimeError("signed attainment error is required")
        return value

    @property
    def absolute_attainment_error(self) -> float:
        value = metric_value(metric_by_id(self.metrics, MetricId.ABSOLUTE_ATTAINMENT_ERROR))
        if value is None:
            raise RuntimeError("absolute attainment error is required")
        return value

    @property
    def relative_error_unavailable_reason(self) -> MetricReason | None:
        return metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR).reason


@dataclass(frozen=True, slots=True)
class SampleEfficiencyPoint:
    """Nested-replicate threshold variability at one calibration size within one seed."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    calibration_size: CalibrationSize
    replicate_count: SubsampleReplicateCount
    mean_threshold: ThresholdValue
    threshold_variance_across_nested_replicates: ThresholdVariance

    def __post_init__(self) -> None:
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("sample-efficiency coordinate must match client and training seed")


def evaluate_threshold_estimate(
    *,
    provenance: ThresholdEstimationProvenance,
    estimated_threshold: ThresholdValue,
    exact_pooled_benign_quantile_reference: ThresholdValue,
    verified_benign_scores: VerifiedHeldOutBenignScores,
) -> ThresholdEstimationDiagnostic:
    """Calculate one declared diagnostic from previously verified benign evidence."""
    if verified_benign_scores.client != provenance.client:
        raise ScientificContractError("threshold diagnostics require scores from the evaluated client")
    if verified_benign_scores.coordinate != provenance.coordinate:
        raise ScientificContractError(
            "threshold diagnostics require score provenance matching the evaluation coordinate"
        )
    scores = verified_benign_scores.scores
    target_exceedance = 1.0 - provenance.quantile.value
    achieved = sum(score.score.exceeds(estimated_threshold) for score in scores) / len(scores)
    signed_attainment_error = achieved - target_exceedance
    absolute_error = abs(estimated_threshold.value - exact_pooled_benign_quantile_reference.value)
    reference = exact_pooled_benign_quantile_reference.value
    relative_metric: MetricAvailability
    if reference == 0.0:
        relative_metric = unavailable(
            MetricId.RELATIVE_THRESHOLD_ERROR,
            MetricStatus.UNDEFINED,
            MetricReason.ZERO_MEAN,
        )
    else:
        relative_metric = available(MetricId.RELATIVE_THRESHOLD_ERROR, absolute_error / abs(reference))
    return ThresholdEstimationDiagnostic(
        provenance=provenance,
        estimated_threshold=estimated_threshold,
        exact_pooled_benign_quantile_reference=exact_pooled_benign_quantile_reference,
        target_exceedance=Ratio(target_exceedance),
        achieved_benign_exceedance=Ratio(achieved),
        metrics=(
            available(MetricId.ABSOLUTE_THRESHOLD_ERROR, absolute_error),
            relative_metric,
            available(MetricId.SIGNED_ATTAINMENT_ERROR, signed_attainment_error),
            available(MetricId.ABSOLUTE_ATTAINMENT_ERROR, abs(signed_attainment_error)),
        ),
    )


def sample_efficiency_curve(
    diagnostics: tuple[ThresholdEstimationDiagnostic, ...],
) -> tuple[SampleEfficiencyPoint, ...]:
    """Summarize nested calibration replicates inside each client/seed/size cell."""
    ordered = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                item.provenance.coordinate.model.value,
                item.provenance.coordinate.preprocessing_identity.value,
                item.provenance.client.client_id,
                item.provenance.training_seed.value,
                item.provenance.calibration_size.value,
            ),
        )
    )
    points: list[SampleEfficiencyPoint] = []
    for key, items in groupby(
        ordered,
        key=lambda item: (
            item.provenance.client,
            item.provenance.coordinate,
            item.provenance.training_seed,
            item.provenance.calibration_size,
        ),
    ):
        replicate_group = tuple(items)
        indexes = tuple(item.provenance.replicate_index.value for item in replicate_group)
        if len(indexes) != len(frozenset(indexes)):
            raise ScientificContractError("nested threshold replicates must be unique within a size cell")
        values = np.asarray(tuple(item.estimated_threshold.value for item in replicate_group), dtype=np.float64)
        points.append(
            SampleEfficiencyPoint(
                client=key[0],
                coordinate=key[1],
                training_seed=key[2],
                calibration_size=key[3],
                replicate_count=SubsampleReplicateCount(len(replicate_group)),
                mean_threshold=ThresholdValue(float(np.mean(values))),
                threshold_variance_across_nested_replicates=ThresholdVariance(float(np.var(values, ddof=0))),
            )
        )
    return tuple(points)
