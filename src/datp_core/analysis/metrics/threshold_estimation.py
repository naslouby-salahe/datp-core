from dataclasses import dataclass
from itertools import groupby

import numpy as np

from datp_core.analysis.metrics.models import (
    MetricAvailability,
    MetricReason,
    MetricStatus,
    metric_by_id,
    validate_metric_set,
)
from datp_core.analysis.metrics.semantics import available, unavailable
from datp_core.analysis.metrics.threshold_evidence import VerifiedHeldOutBenignScores
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    CalibrationSize,
    MetricValue,
    Quantile,
    Ratio,
    RelativeThresholdError,
    ReplicateIndex,
    Seed,
    SubsampleReplicateCount,
    ThresholdValue,
    ThresholdVariance,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate

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
            raise ScientificContractError(
                ErrorMessage("threshold-estimation coordinate must match client and training seed")
            )


@dataclass(frozen=True, slots=True)
class ThresholdEstimationDiagnostic:
    provenance: ThresholdEstimationProvenance
    estimated_threshold: ThresholdValue
    exact_pooled_benign_quantile_reference: ThresholdValue
    target_exceedance: Ratio
    achieved_benign_exceedance: Ratio
    metrics: tuple[MetricAvailability, ...]

    def __post_init__(self) -> None:
        validate_metric_set(self.metrics, _THRESHOLD_ESTIMATION_METRICS)
        metrics_dict = {m.metric: m for m in self.metrics}

        absolute_threshold = metrics_dict[MetricId.ABSOLUTE_THRESHOLD_ERROR]
        relative_threshold = metrics_dict[MetricId.RELATIVE_THRESHOLD_ERROR]
        signed_attainment = metrics_dict[MetricId.SIGNED_ATTAINMENT_ERROR]
        absolute_attainment = metrics_dict[MetricId.ABSOLUTE_ATTAINMENT_ERROR]

        if absolute_threshold.value is None or signed_attainment.value is None or absolute_attainment.value is None:
            raise ScientificContractError(
                ErrorMessage("absolute and attainment threshold diagnostics must be available")
            )
        if absolute_threshold.value.value < 0 or absolute_attainment.value.value < 0:
            raise ScientificContractError(ErrorMessage("absolute threshold diagnostics must be non-negative"))
        if relative_threshold.value is None and relative_threshold.reason is not MetricReason.ZERO_MEAN:
            raise ScientificContractError(
                ErrorMessage("undefined relative threshold error requires a zero-reference reason")
            )

        expected_signed = self.achieved_benign_exceedance.value - self.target_exceedance.value
        if signed_attainment.value.value != expected_signed:
            raise ScientificContractError(
                ErrorMessage("signed attainment error must match achieved minus target exceedance")
            )

    @property
    def absolute_threshold_error(self) -> AbsoluteThresholdError:
        result = metric_by_id(self.metrics, MetricId.ABSOLUTE_THRESHOLD_ERROR).value
        if result is None:
            raise ScientificContractError(ErrorMessage("absolute threshold error must be available"))
        return AbsoluteThresholdError(result.value)

    @property
    def relative_threshold_error_status(self) -> MetricStatus:
        return metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR).status

    @property
    def relative_threshold_error(self) -> RelativeThresholdError | None:
        result = metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR).value
        return None if result is None else RelativeThresholdError(result.value)

    @property
    def signed_attainment_error(self) -> MetricValue:
        result = metric_by_id(self.metrics, MetricId.SIGNED_ATTAINMENT_ERROR).value
        if result is None:
            raise ScientificContractError(ErrorMessage("signed attainment error must be available"))
        return result

    @property
    def absolute_attainment_error(self) -> MetricValue:
        result = metric_by_id(self.metrics, MetricId.ABSOLUTE_ATTAINMENT_ERROR).value
        if result is None:
            raise ScientificContractError(ErrorMessage("absolute attainment error must be available"))
        return result

    @property
    def relative_error_unavailable_reason(self) -> MetricReason | None:
        return metric_by_id(self.metrics, MetricId.RELATIVE_THRESHOLD_ERROR).reason


@dataclass(frozen=True, slots=True)
class SampleEfficiencyPoint:
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
            raise ScientificContractError(
                ErrorMessage("sample-efficiency coordinate must match client and training seed")
            )


def evaluate_threshold_estimate(
    *,
    provenance: ThresholdEstimationProvenance,
    estimated_threshold: ThresholdValue,
    exact_pooled_benign_quantile_reference: ThresholdValue,
    verified_benign_scores: VerifiedHeldOutBenignScores,
) -> ThresholdEstimationDiagnostic:
    if verified_benign_scores.client != provenance.client:
        raise ScientificContractError(ErrorMessage("threshold diagnostics require scores from the evaluated client"))
    if verified_benign_scores.coordinate != provenance.coordinate:
        raise ScientificContractError(
            ErrorMessage("threshold diagnostics require score provenance matching the evaluation coordinate")
        )

    scores = verified_benign_scores.scores
    target_exceedance = 1.0 - provenance.quantile.value

    achieved_count = sum(1 for score in scores if score.score.exceeds(estimated_threshold))
    achieved = achieved_count / len(scores)

    signed_attainment_error = achieved - target_exceedance
    absolute_error = abs(estimated_threshold.value - exact_pooled_benign_quantile_reference.value)
    reference = exact_pooled_benign_quantile_reference.value

    if reference == 0.0:
        relative_metric = unavailable(
            MetricId.RELATIVE_THRESHOLD_ERROR,
            MetricStatus.UNDEFINED,
            MetricReason.ZERO_MEAN,
        )
    else:
        relative_metric = available(MetricId.RELATIVE_THRESHOLD_ERROR, MetricValue(absolute_error / abs(reference)))

    return ThresholdEstimationDiagnostic(
        provenance=provenance,
        estimated_threshold=estimated_threshold,
        exact_pooled_benign_quantile_reference=exact_pooled_benign_quantile_reference,
        target_exceedance=Ratio(target_exceedance),
        achieved_benign_exceedance=Ratio(achieved),
        metrics=(
            available(MetricId.ABSOLUTE_THRESHOLD_ERROR, MetricValue(absolute_error)),
            relative_metric,
            available(MetricId.SIGNED_ATTAINMENT_ERROR, MetricValue(signed_attainment_error)),
            available(MetricId.ABSOLUTE_ATTAINMENT_ERROR, MetricValue(abs(signed_attainment_error))),
        ),
    )


def sample_efficiency_curve(
    diagnostics: tuple[ThresholdEstimationDiagnostic, ...],
) -> tuple[SampleEfficiencyPoint, ...]:
    def get_group_key(item: ThresholdEstimationDiagnostic):
        return (
            item.provenance.client,
            item.provenance.coordinate,
            item.provenance.training_seed,
            item.provenance.calibration_size,
        )

    def get_sort_key(item: ThresholdEstimationDiagnostic):
        return (
            item.provenance.coordinate.model.value,
            item.provenance.coordinate.preprocessing_identity.value,
            item.provenance.client.client_id.value,
            item.provenance.training_seed.value,
            item.provenance.calibration_size.value,
        )

    ordered = tuple(sorted(diagnostics, key=get_sort_key))
    points: list[SampleEfficiencyPoint] = []

    for key, items in groupby(ordered, key=get_group_key):
        replicate_group = tuple(items)
        indexes = tuple(item.provenance.replicate_index.value for item in replicate_group)

        if len(indexes) != len(set(indexes)):
            raise ScientificContractError(ErrorMessage("nested threshold replicates must be unique within a size cell"))

        values = np.fromiter((item.estimated_threshold.value for item in replicate_group), dtype=np.float64)

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
