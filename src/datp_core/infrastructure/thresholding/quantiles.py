from dataclasses import dataclass
from typing import Protocol, assert_never

from datp_core.application.ports.thresholding import QuantileEstimateRequest, QuantileEstimateResult, QuantileEstimator
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    ClientMap,
    ClientMapEntry,
    QuantileEstimatorType,
    ThresholdAssignmentSet,
)
from datp_core.domain.mathematics.quantiles import exact_quantile, exact_weighted_quantile
from datp_core.domain.thresholding.policies import ThresholdPercentile, ThresholdValue


class CalibrationScoreReader(Protocol):
    def read(self, *, calibration_scores: CalibrationScoreArtifactSet, client_index: int) -> tuple[float, ...]: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ExactQuantileEstimator(QuantileEstimator):
    estimator: QuantileEstimatorType
    reader: CalibrationScoreReader

    def estimate(self, request: QuantileEstimateRequest) -> QuantileEstimateResult:
        estimates = self._estimate_values(calibration_scores=request.calibration_scores, percentile=request.percentile)
        return QuantileEstimateResult(estimates=estimates)

    def _estimate_values(
        self,
        *,
        calibration_scores: CalibrationScoreArtifactSet,
        percentile: ThresholdPercentile,
    ) -> ThresholdAssignmentSet:
        client_scores = self._client_scores(calibration_scores=calibration_scores)
        threshold_values = self._threshold_values(client_scores=client_scores, percentile=percentile)
        roster = calibration_scores.per_client.values.roster
        return ThresholdAssignmentSet(
            values=ClientMap(
                roster=roster,
                entries=tuple(
                    ClientMapEntry(client_id=client_id, value=threshold_value)
                    for client_id, threshold_value in zip(roster.client_ids, threshold_values, strict=True)
                ),
            )
        )

    def _client_scores(self, *, calibration_scores: CalibrationScoreArtifactSet) -> tuple[tuple[float, ...], ...]:
        return tuple(
            self.reader.read(calibration_scores=calibration_scores, client_index=index)
            for index, _ in enumerate(calibration_scores.per_client.values.entries)
        )

    def _threshold_values(
        self,
        *,
        client_scores: tuple[tuple[float, ...], ...],
        percentile: ThresholdPercentile,
    ) -> tuple[ThresholdValue, ...]:
        match self.estimator:
            case QuantileEstimatorType.LOCAL_EXACT:
                return tuple(
                    ThresholdValue(value=exact_quantile(values=scores, percentile=percentile))
                    for scores in client_scores
                )
            case QuantileEstimatorType.POOLED_EXACT | QuantileEstimatorType.CENTRALIZED_ORACLE:
                pooled = exact_quantile(
                    values=tuple(score for scores in client_scores for score in scores),
                    percentile=percentile,
                )
                return tuple(ThresholdValue(value=pooled) for _ in client_scores)
            case QuantileEstimatorType.WEIGHTED_EXACT:
                local = tuple(exact_quantile(values=scores, percentile=percentile) for scores in client_scores)
                weighted = exact_weighted_quantile(
                    values=local,
                    weights=tuple(len(scores) for scores in client_scores),
                    percentile=percentile,
                )
                return tuple(ThresholdValue(value=weighted) for _ in client_scores)
            case _ as unreachable:
                assert_never(unreachable)
