from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, ThresholdEstimator, ValidationLabel
from datp_core.core.numeric import RowCount, ScoreMoment, ScoreVariance, ThresholdValue
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import ThresholdAssignment
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, require_eligible_cohort, unweighted_mean


@dataclass(frozen=True, slots=True)
class MomentLocalThreshold:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    mean: ScoreMoment
    sample_variance: ScoreVariance
    calibration_count: RowCount
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True)
class MomentSharedThresholdResult:
    coordinate: FederatedTrainingCoordinate
    estimator: ThresholdEstimator
    local_thresholds: tuple[MomentLocalThreshold, ...]
    shared_threshold: ThresholdValue
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SHARED_THRESHOLD


@dataclass(frozen=True, slots=True)
class MomentLocalThresholdResult:
    coordinate: FederatedTrainingCoordinate
    estimator: ThresholdEstimator
    local_thresholds: tuple[MomentLocalThreshold, ...]
    assignments: tuple[ThresholdAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_THRESHOLD


def _local_threshold(scores: ClientBenignCalibrationScores) -> MomentLocalThreshold:
    if len(scores.scores) < 2:
        raise ScientificContractError(ErrorMessage("moment threshold requires at least two calibration scores"))
    values = scores.as_array
    mean = ScoreMoment(float(np.mean(values, dtype=np.float64)))
    variance = ScoreVariance(float(np.var(values, ddof=1, dtype=np.float64)))
    return MomentLocalThreshold(
        client=scores.client,
        coordinate=scores.coordinate,
        mean=mean,
        sample_variance=variance,
        calibration_count=RowCount(len(scores.scores)),
        threshold=ThresholdValue(mean.value + float(np.sqrt(variance.value))),
    )


def construct_moment_shared_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
) -> MomentSharedThresholdResult:
    require_eligible_cohort(eligible, ValidationLabel("moment shared threshold construction"))
    local = tuple(_local_threshold(item) for item in eligible)
    shared = unweighted_mean(tuple(item.threshold for item in local))
    return MomentSharedThresholdResult(
        coordinate=eligible[0].coordinate,
        estimator=ThresholdEstimator.MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR,
        local_thresholds=local,
        shared_threshold=shared,
        assignments=tuple(ThresholdAssignment(item.client, shared) for item in local),
    )


def construct_moment_local_threshold(
    eligible: tuple[ClientBenignCalibrationScores, ...],
) -> MomentLocalThresholdResult:
    require_eligible_cohort(eligible, ValidationLabel("moment local threshold construction"))
    local = tuple(_local_threshold(item) for item in eligible)
    return MomentLocalThresholdResult(
        coordinate=eligible[0].coordinate,
        estimator=ThresholdEstimator.MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR,
        local_thresholds=local,
        assignments=tuple(ThresholdAssignment(item.client, item.threshold) for item in local),
    )
