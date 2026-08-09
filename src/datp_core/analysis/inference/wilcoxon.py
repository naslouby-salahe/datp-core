"""Generic paired-inference contracts, Wilcoxon testing, and rank-biserial effect size."""

from enum import StrEnum
from math import isfinite
from typing import ClassVar, Protocol, SupportsFloat, cast

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator
from scipy import stats

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.inference.contracts import (
    PairedInferenceProtocol,
    WilcoxonComputationPreference,
    WilcoxonZeroMethod,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    AvailabilityStatus,
    EffectSizeId,
    StatisticalTestId,
)
from datp_core.core.numeric import (
    ClosedUnitIntervalValue,
    MetricValue,
    PairedObservationCount,
    RankSum,
)


class StatisticPValueResult(Protocol):
    statistic: SupportsFloat
    pvalue: SupportsFloat


def statistic_p_value(
    result: StatisticPValueResult,
) -> (
    tuple[float, float] | None
):  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    statistic, pvalue = float(result.statistic), float(result.pvalue)
    if not all(isfinite(value) for value in (statistic, pvalue)):
        return None
    return statistic, pvalue


class WilcoxonComputationMethod(StrEnum):
    EXACT = "exact"
    ASYMPTOTIC = "asymptotic"


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
    effective_sample_size: PairedObservationCount
    requested_method: WilcoxonComputationPreference | None
    computation_method: WilcoxonComputationMethod | None
    zero_method: WilcoxonZeroMethod | None
    availability: AvailabilityStatus
    reason: (
        str | None
    )  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    fallback_reason: (
        str | None
    )  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity

    @model_validator(mode="after")
    def validate_result(self) -> "WilcoxonResult":
        available = self.availability is AvailabilityStatus.AVAILABLE
        if available:
            valid = (
                self.statistic is not None
                and self.p_value is not None
                and self.computation_method is not None
                and self.requested_method is not None
                and self.zero_method is not None
                and self.reason is None
            )
            if self.computation_method is WilcoxonComputationMethod.EXACT and self.fallback_reason is not None:
                valid = False
            if self.computation_method is WilcoxonComputationMethod.ASYMPTOTIC and self.fallback_reason is None:
                valid = False
        else:
            valid = (
                self.statistic is None
                and self.p_value is None
                and self.computation_method is None
                and self.reason is not None
                and self.fallback_reason is None
            )
        if not valid:
            raise ValueError("Wilcoxon availability and values are inconsistent")
        return self


class RankBiserialResult(StrictModel):
    value: CorrelationCoefficient | None
    positive_rank_sum: RankSum | None
    negative_rank_sum: RankSum | None
    nonzero_pair_count: PairedObservationCount
    availability: AvailabilityStatus
    reason: (
        str | None
    )  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity

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


def paired_wilcoxon(contrasts: PairedContrasts, protocol: PairedInferenceProtocol) -> WilcoxonResult:
    if len(contrasts) != protocol.paired_seed_count.value:
        return blocked_wilcoxon("paired contrast count does not match the declared inference protocol")
    if protocol.statistical_test is not StatisticalTestId.WILCOXON_SIGNED_RANK:
        raise ValueError("paired Wilcoxon requires the Wilcoxon signed-rank protocol")
    if protocol.wilcoxon_computation_preference is not WilcoxonComputationPreference.EXACT_PREFERRED:
        raise ValueError("paired Wilcoxon requires the exact-preferred computation policy")
    deltas = paired_deltas(contrasts)
    nonzero_pair_count = PairedObservationCount(int(np.count_nonzero(deltas)))
    effective_sample_size = PairedObservationCount(int(deltas.size))
    if nonzero_pair_count.value == 0:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            effective_sample_size=effective_sample_size,
            requested_method=protocol.wilcoxon_computation_preference,
            computation_method=None,
            zero_method=protocol.wilcoxon_zero_method,
            availability=AvailabilityStatus.UNDEFINED,
            reason="Wilcoxon requires at least one nonzero paired difference",
            fallback_reason=None,
        )
    method, fallback_reason = _select_wilcoxon_method(deltas, protocol)
    result = cast(
        StatisticPValueResult,
        stats.wilcoxon(
            deltas,
            alternative=protocol.wilcoxon_alternative.value,
            zero_method=protocol.wilcoxon_zero_method.value,
            method=method.value,
        ),
    )
    extracted = statistic_p_value(result)
    if extracted is None:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            effective_sample_size=effective_sample_size,
            requested_method=protocol.wilcoxon_computation_preference,
            computation_method=None,
            zero_method=protocol.wilcoxon_zero_method,
            availability=AvailabilityStatus.UNAVAILABLE,
            reason="SciPy Wilcoxon result does not expose finite statistic and p-value values",
            fallback_reason=None,
        )
    statistic, p_value = extracted
    return WilcoxonResult(
        statistic=RankSum(statistic),
        p_value=PValue(p_value),
        nonzero_pair_count=nonzero_pair_count,
        effective_sample_size=effective_sample_size,
        requested_method=protocol.wilcoxon_computation_preference,
        computation_method=method,
        zero_method=protocol.wilcoxon_zero_method,
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
        fallback_reason=fallback_reason,
    )


def matched_pairs_rank_biserial(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
) -> RankBiserialResult:
    if len(contrasts) != protocol.paired_seed_count.value:
        return blocked_rank_biserial("paired contrast count does not match the declared inference protocol")
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
            reason="rank-biserial correlation requires at least one nonzero paired difference",
        )
    ranks = np.asarray(stats.rankdata(np.abs(nonzero), method="average"), dtype=np.float64)
    positive_rank_sum = float(np.sum(ranks[nonzero > 0.0]))
    negative_rank_sum = float(np.sum(ranks[nonzero < 0.0]))
    rank_total = float(np.sum(ranks))
    return RankBiserialResult(
        value=CorrelationCoefficient((positive_rank_sum - negative_rank_sum) / rank_total),
        positive_rank_sum=RankSum(positive_rank_sum),
        negative_rank_sum=RankSum(negative_rank_sum),
        nonzero_pair_count=PairedObservationCount(int(nonzero.size)),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )


def blocked_wilcoxon(
    reason: str,
) -> WilcoxonResult:  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    return WilcoxonResult(
        statistic=None,
        p_value=None,
        nonzero_pair_count=PairedObservationCount(0),
        effective_sample_size=PairedObservationCount(0),
        requested_method=None,
        computation_method=None,
        zero_method=None,
        availability=AvailabilityStatus.UNAVAILABLE,
        reason=reason,
        fallback_reason=None,
    )


def blocked_rank_biserial(
    reason: str,
) -> RankBiserialResult:  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    return RankBiserialResult(
        value=None,
        positive_rank_sum=None,
        negative_rank_sum=None,
        nonzero_pair_count=PairedObservationCount(0),
        availability=AvailabilityStatus.UNAVAILABLE,
        reason=reason,
    )


def _select_wilcoxon_method(
    deltas: NDArray[np.float64],
    protocol: PairedInferenceProtocol,
) -> tuple[
    WilcoxonComputationMethod, str | None
]:  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists. Adapt all usage and callers. No backwards compatiblity
    zero_method = protocol.wilcoxon_zero_method.value
    alternative = protocol.wilcoxon_alternative.value
    nonzero = deltas[deltas != 0.0]
    if nonzero.size == 0:
        return (
            WilcoxonComputationMethod.ASYMPTOTIC,
            "exact Wilcoxon unavailable: no non-zero differences after declared zero handling",
        )
    absolute = np.abs(nonzero)
    if absolute.size != len({float(value) for value in absolute}):
        return (
            WilcoxonComputationMethod.ASYMPTOTIC,
            "exact Wilcoxon unavailable: absolute paired differences contain ties",
        )
    zero_count = int(deltas.size - nonzero.size)
    if zero_count > 0:
        return (
            WilcoxonComputationMethod.ASYMPTOTIC,
            (
                "exact Wilcoxon unavailable: zero differences are present with "
                f"declared zero handling `{zero_method}` (zeros={zero_count})"
            ),
        )
    try:
        result = stats.wilcoxon(
            deltas,
            alternative=alternative,
            zero_method=zero_method,
            method="exact",
        )
    except ValueError as error:
        return WilcoxonComputationMethod.ASYMPTOTIC, f"exact Wilcoxon unavailable: {error}"
    extracted = statistic_p_value(cast(StatisticPValueResult, result))
    if extracted is None:
        return (
            WilcoxonComputationMethod.ASYMPTOTIC,
            "exact Wilcoxon unavailable: SciPy exact path did not return finite statistic and p-value",
        )
    return WilcoxonComputationMethod.EXACT, None
