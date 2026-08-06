"""Paired Wilcoxon inference and matched-pairs rank-biserial effect size."""

from typing import ClassVar, cast

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator
from scipy import stats

from datp_core.analysis.adapters.scipy import StatisticPValueResult, statistic_p_value
from datp_core.analysis.contrasts import PairedContrasts
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EffectSizeId, StatisticalTestId
from datp_core.domain.values.base import ClosedUnitIntervalValue
from datp_core.domain.values.counts import PairedObservationCount
from datp_core.domain.values.ratios import MetricValue, RankSum
from datp_core.protocols.statistics import (
    PairedInferenceProtocol,
    WilcoxonComputationMethod,
)


class PValue(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "p-value"


class CorrelationCoefficient(MetricValue):
    validation_name: ClassVar[str] = "correlation coefficient"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not -1.0 <= self.value <= 1.0:
            raise ValueError("correlation coefficient must lie in [-1, 1]")


class WilcoxonResult(StrictModel):
    statistic: RankSum | None
    p_value: PValue | None
    nonzero_pair_count: PairedObservationCount
    computation_method: WilcoxonComputationMethod | None
    availability: AvailabilityStatus
    reason: str | None

    @model_validator(mode="after")
    def validate_result(self) -> "WilcoxonResult":
        available = self.availability is AvailabilityStatus.AVAILABLE
        if available:
            valid = (
                self.statistic is not None
                and self.p_value is not None
                and self.computation_method is not None
                and self.reason is None
            )
        else:
            valid = self.statistic is None and self.p_value is None and self.reason is not None
        if not valid:
            raise ValueError("Wilcoxon availability and values are inconsistent")
        return self


class RankBiserialResult(StrictModel):
    value: CorrelationCoefficient | None
    positive_rank_sum: RankSum | None
    negative_rank_sum: RankSum | None
    nonzero_pair_count: PairedObservationCount
    availability: AvailabilityStatus
    reason: str | None

    @model_validator(mode="after")
    def validate_result(self) -> "RankBiserialResult":
        values = (self.value, self.positive_rank_sum, self.negative_rank_sum)
        available = self.availability is AvailabilityStatus.AVAILABLE
        valid = (
            all(item is not None for item in values) and self.reason is None
            if available
            else all(item is None for item in values) and self.reason is not None
        )
        if not valid:
            raise ValueError("rank-biserial availability and values are inconsistent")
        return self


def paired_deltas(contrasts: PairedContrasts) -> NDArray[np.float64]:
    values = np.fromiter(
        (contrast.delta.value for contrast in contrasts),
        dtype=np.float64,
        count=len(contrasts),
    )
    if np.any(~np.isfinite(values)):
        raise ValueError("paired contrasts must be finite")
    return values


def paired_wilcoxon(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
) -> WilcoxonResult:
    if protocol.statistical_test is not StatisticalTestId.WILCOXON_SIGNED_RANK:
        raise ValueError("paired Wilcoxon requires the Wilcoxon signed-rank protocol")
    deltas = paired_deltas(contrasts)
    nonzero_pair_count = PairedObservationCount(int(np.count_nonzero(deltas)))
    if nonzero_pair_count.value == 0:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=None,
            availability=AvailabilityStatus.UNDEFINED,
            reason="Wilcoxon requires at least one nonzero paired difference",
        )
    result = cast(
        StatisticPValueResult,
        stats.wilcoxon(
            deltas,
            alternative=protocol.wilcoxon_alternative.value,
            zero_method=protocol.wilcoxon_zero_method.value,
            method=protocol.wilcoxon_computation_method.value,
        ),
    )
    extracted = statistic_p_value(result)
    if extracted is None:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=WilcoxonComputationMethod.SCIPY_ASYMPTOTIC,
            availability=AvailabilityStatus.UNAVAILABLE,
            reason=("SciPy Wilcoxon result does not expose finite statistic and p-value values"),
        )
    statistic, p_value = extracted
    return WilcoxonResult(
        statistic=RankSum(statistic),
        p_value=PValue(p_value),
        nonzero_pair_count=nonzero_pair_count,
        computation_method=WilcoxonComputationMethod.SCIPY_ASYMPTOTIC,
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )


def matched_pairs_rank_biserial(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
) -> RankBiserialResult:
    if protocol.effect_size is not EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL:
        raise ValueError("paired effect size requires matched-pairs rank-biserial correlation")
    deltas = paired_deltas(contrasts)
    nonzero = deltas[deltas != 0.0]
    if not nonzero.size:
        return RankBiserialResult(
            value=None,
            positive_rank_sum=None,
            negative_rank_sum=None,
            nonzero_pair_count=PairedObservationCount(0),
            availability=AvailabilityStatus.UNDEFINED,
            reason=("rank-biserial correlation requires at least one nonzero paired difference"),
        )
    ranks = stats.rankdata(np.abs(nonzero), method="average")
    positive_rank_sum = float(np.sum(ranks[nonzero > 0.0]))
    negative_rank_sum = float(np.sum(ranks[nonzero < 0.0]))
    rank_total = float(ranks.sum())
    return RankBiserialResult(
        value=CorrelationCoefficient((positive_rank_sum - negative_rank_sum) / rank_total),
        positive_rank_sum=RankSum(positive_rank_sum),
        negative_rank_sum=RankSum(negative_rank_sum),
        nonzero_pair_count=PairedObservationCount(int(nonzero.size)),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )
