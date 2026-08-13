from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

import numpy as np
from pydantic import model_validator

from datp_core.analysis.contrasts import MetricSeries, PairedDifferenceCounts
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, EvidenceRole, FederatedThresholdMethod
from datp_core.core.numeric import MetricValue, PairedObservationCount, Quantile, Ratio, Seed, is_numeric_zero
from datp_core.data.populations.contracts import ClientIdentity


class QuantileRange(StrictModel):
    lower: Ratio
    upper: Ratio

    @model_validator(mode="after")
    def validate_range(self) -> "QuantileRange":
        if self.lower.value > self.upper.value:
            raise ValueError("descriptive lower quantile cannot exceed the upper quantile")
        return self


class ObservationCounts(StrictModel):
    unavailable: PairedObservationCount
    excluded: PairedObservationCount


class DescriptiveStatistics(StrictModel):
    mean: MetricValue
    median: MetricValue
    lower_quantile_value: MetricValue
    upper_quantile_value: MetricValue
    minimum: MetricValue
    maximum: MetricValue

    @model_validator(mode="after")
    def validate_order(self) -> "DescriptiveStatistics":
        values = (
            self.minimum.value,
            self.lower_quantile_value.value,
            self.median.value,
            self.upper_quantile_value.value,
            self.maximum.value,
        )
        if values != tuple(sorted(values)):
            raise ValueError("descriptive statistics must preserve their declared order")
        return self

    @property
    def spread(self) -> MetricValue:
        return MetricValue(self.maximum.value - self.minimum.value)


class CrossSeedMetricSummary(StrictModel):
    mean: MetricValue | None
    coefficient_of_variation: MetricValue | None


class DescriptiveSummary(StrictModel):
    evidence_role: EvidenceRole
    values: MetricSeries
    counts: ObservationCounts
    quantiles: QuantileRange
    statistics: DescriptiveStatistics | None
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_summary(self) -> "DescriptiveSummary":
        if self.values:
            if self.statistics is None or self.reason is not None:
                raise ValueError("available descriptive values require statistics and no reason")
        elif self.statistics is not None or self.reason is None:
            raise ValueError("unavailable descriptive values require no statistics and an explicit reason")
        return self

    @property
    def available_count(self) -> PairedObservationCount:
        return PairedObservationCount(len(self.values))

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.values else AvailabilityStatus.UNAVAILABLE


def summarize_values(
    values: MetricSeries,
    *,
    evidence_role: EvidenceRole,
    counts: ObservationCounts,
    quantiles: QuantileRange,
) -> DescriptiveSummary:
    if not values:
        return DescriptiveSummary(
            evidence_role=evidence_role,
            values=(),
            counts=counts,
            quantiles=quantiles,
            statistics=None,
            reason=AnalysisReasonText("no available values"),
        )
    array = _metric_array(values)
    return DescriptiveSummary(
        evidence_role=evidence_role,
        values=values,
        counts=counts,
        quantiles=quantiles,
        statistics=DescriptiveStatistics(
            mean=MetricValue(float(np.mean(array))),
            median=MetricValue(float(np.median(array))),
            lower_quantile_value=MetricValue(
                float(
                    np.quantile(
                        array,
                        quantiles.lower.value,
                        method="linear",
                    )
                )
            ),
            upper_quantile_value=MetricValue(
                float(
                    np.quantile(
                        array,
                        quantiles.upper.value,
                        method="linear",
                    )
                )
            ),
            minimum=MetricValue(float(np.min(array))),
            maximum=MetricValue(float(np.max(array))),
        ),
        reason=None,
    )


def summarize_cross_seed_metric_values(values: MetricSeries) -> CrossSeedMetricSummary:
    if not values:
        return CrossSeedMetricSummary(mean=None, coefficient_of_variation=None)
    mean = MetricValue(sum(value.value for value in values) / len(values))
    if len(values) < 2:
        return CrossSeedMetricSummary(mean=mean, coefficient_of_variation=None)
    if mean.value == 0:
        return CrossSeedMetricSummary(mean=mean, coefficient_of_variation=None)
    variance = sum((value.value - mean.value) ** 2 for value in values) / (len(values) - 1)
    return CrossSeedMetricSummary(
        mean=mean,
        coefficient_of_variation=MetricValue(variance**0.5 / mean.value),
    )


def count_paired_differences(values: MetricSeries) -> PairedDifferenceCounts:
    return PairedDifferenceCounts(
        positive=PairedObservationCount(sum(value.value > 0.0 for value in values)),
        zero=PairedObservationCount(sum(is_numeric_zero(value.value) for value in values)),
        negative=PairedObservationCount(sum(value.value < 0.0 for value in values)),
    )


def _metric_array(values: MetricSeries) -> np.ndarray:
    array = np.fromiter(
        (value.value for value in values),
        dtype=np.float64,
        count=len(values),
    )
    if np.any(~np.isfinite(array)):
        raise ValueError("metric values must be finite")
    return array


class ScoreRole(StrEnum):
    BENIGN_CALIBRATION = "benign_calibration"
    BENIGN_EVALUATION = "benign_evaluation"
    ATTACK_EVALUATION = "attack_evaluation"


class EmpiricalCdfPoint(StrictModel):
    score: MetricValue
    cumulative_probability: Ratio


class ClientScoreGeometry(StrictModel):
    client: ClientIdentity
    score_role: ScoreRole
    scores: tuple[MetricValue, ...]
    quantiles: tuple[MetricValue, ...]
    empirical_cdf: tuple[EmpiricalCdfPoint, ...]
    mean: MetricValue | None
    standard_deviation: MetricValue | None
    minimum: MetricValue | None
    maximum: MetricValue | None
    unavailable_reason: AnalysisReasonText | None = None

    @model_validator(mode="after")
    def validate_geometry(self) -> "ClientScoreGeometry":
        if self.unavailable_reason is not None:
            if self.scores or self.empirical_cdf or self.mean is not None:
                raise ValueError("unavailable score geometry cannot carry scores, CDF points, or summaries")
            return self
        if not self.scores or not self.empirical_cdf:
            raise ValueError("available score geometry requires scores and empirical CDF points")
        if self.mean is None or self.standard_deviation is None or self.minimum is None or self.maximum is None:
            raise ValueError("available score geometry requires distribution summaries")
        return self


class ScoreGeometryThresholdOverlay(StrictModel):
    method: FederatedThresholdMethod
    threshold: MetricValue
    client: ClientIdentity | None = None
    benign_exceedance: MetricValue | None = None
    attack_acceptance: MetricValue | None = None
    balanced_accuracy: MetricValue | None = None
    macro_f1: MetricValue | None = None


class ScoreGeometryResult(StrictModel):
    seed: Seed
    common_support_lower: MetricValue | None
    common_support_upper: MetricValue | None
    clients: tuple[ClientScoreGeometry, ...]
    threshold_overlays: tuple[ScoreGeometryThresholdOverlay, ...]
    attack_geometry_available: bool
    attack_geometry_reason: AnalysisReasonText | None = None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.clients else AvailabilityStatus.UNAVAILABLE


_DEFAULT_CDF_QUANTILES: tuple[Quantile, ...] = (
    Quantile(0.05),
    Quantile(0.25),
    Quantile(0.5),
    Quantile(0.75),
    Quantile(0.95),
)


def empirical_cdf_points(scores: tuple[MetricValue, ...]) -> tuple[EmpiricalCdfPoint, ...]:
    if not scores:
        raise ValueError("empirical CDF requires at least one score")
    ordered = tuple(sorted(score.value for score in scores))
    count = len(ordered)
    return tuple(
        EmpiricalCdfPoint(
            score=MetricValue(value),
            cumulative_probability=Ratio((index + 1) / count),
        )
        for index, value in enumerate(ordered)
    )


def client_score_geometry(
    *,
    client: ClientIdentity,
    score_role: ScoreRole,
    scores: tuple[MetricValue, ...],
    quantiles: tuple[Quantile, ...] = _DEFAULT_CDF_QUANTILES,
) -> ClientScoreGeometry:
    if not scores:
        return ClientScoreGeometry(
            client=client,
            score_role=score_role,
            scores=(),
            quantiles=(),
            empirical_cdf=(),
            mean=None,
            standard_deviation=None,
            minimum=None,
            maximum=None,
            unavailable_reason=AnalysisReasonText("no scores available for the declared role"),
        )
    array = _metric_array(scores)
    quantile_values = tuple(MetricValue(float(np.quantile(array, level.value, method="linear"))) for level in quantiles)
    return ClientScoreGeometry(
        client=client,
        score_role=score_role,
        scores=scores,
        quantiles=quantile_values,
        empirical_cdf=empirical_cdf_points(scores),
        mean=MetricValue(float(np.mean(array))),
        standard_deviation=MetricValue(float(np.std(array, ddof=0))),
        minimum=MetricValue(float(np.min(array))),
        maximum=MetricValue(float(np.max(array))),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientEvaluationScoreSeries:
    client: ClientIdentity
    scores: tuple[MetricValue, ...]


def score_geometry_from_client_vectors(
    *,
    seed: Seed,
    benign_evaluation: tuple[ClientEvaluationScoreSeries, ...],
    attack_evaluation: tuple[ClientEvaluationScoreSeries, ...] | None,
    threshold_overlays: tuple[ScoreGeometryThresholdOverlay, ...],
    attack_geometry_available: bool,
    attack_geometry_reason: AnalysisReasonText | None = None,
) -> ScoreGeometryResult:
    clients = tuple(
        client_score_geometry(client=item.client, score_role=ScoreRole.BENIGN_EVALUATION, scores=item.scores)
        for item in sorted(benign_evaluation, key=lambda item: item.client)
    )
    if attack_evaluation is not None and attack_geometry_available:
        clients = clients + tuple(
            client_score_geometry(client=item.client, score_role=ScoreRole.ATTACK_EVALUATION, scores=item.scores)
            for item in sorted(attack_evaluation, key=lambda item: item.client)
        )
    available = tuple(
        item
        for item in clients
        if item.unavailable_reason is None and item.scores and item.minimum is not None and item.maximum is not None
    )
    if available:
        lower = MetricValue(min(item.minimum.value for item in available if item.minimum is not None))
        upper = MetricValue(max(item.maximum.value for item in available if item.maximum is not None))
    else:
        lower = upper = None
    return ScoreGeometryResult(
        seed=seed,
        common_support_lower=lower,
        common_support_upper=upper,
        clients=clients,
        threshold_overlays=threshold_overlays,
        attack_geometry_available=attack_geometry_available,
        attack_geometry_reason=attack_geometry_reason,
    )
