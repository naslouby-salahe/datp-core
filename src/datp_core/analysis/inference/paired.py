"""Wilcoxon signed-rank, rank-biserial correlation, Holm correction, and sign consistency."""

from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

from datp_core.analysis.descriptive import PairedDifferenceCounts, count_paired_differences
from datp_core.analysis.inference.bootstrap import _deltas
from datp_core.domain.enums import AvailabilityStatus, EffectSizeId, MultiplicityCorrectionId, StatisticalTestId
from datp_core.domain.values import Ratio


@dataclass(frozen=True, slots=True)
class WilcoxonResult:
    test: StatisticalTestId
    alternative: str
    zero_method: str
    computation_method: str
    statistic: float | None
    p_value: float | None
    nonzero_pair_count: int
    availability: AvailabilityStatus
    reason: str


@dataclass(frozen=True, slots=True)
class RankBiserialResult:
    effect_size: EffectSizeId
    value: float | None
    positive_rank_sum: float | None
    negative_rank_sum: float | None
    nonzero_pair_count: int
    availability: AvailabilityStatus
    reason: str


@dataclass(frozen=True, slots=True)
class MultiplicityResult:
    correction: MultiplicityCorrectionId
    family_name: str
    raw_p_values: tuple[float, ...]
    adjusted_p_values: tuple[float, ...]
    rejected: tuple[bool, ...]

    def __post_init__(self) -> None:
        if not self.family_name or not self.raw_p_values:
            raise ValueError("multiplicity requires a predeclared non-empty family")
        if len(self.raw_p_values) != len(self.adjusted_p_values) or len(self.raw_p_values) != len(self.rejected):
            raise ValueError("multiplicity result lengths must agree")
        if any(not 0 <= value <= 1 for value in (*self.raw_p_values, *self.adjusted_p_values)):
            raise ValueError("p-values must lie in [0, 1]")


def paired_wilcoxon(
    contrasts: tuple,
) -> WilcoxonResult:
    deltas = _deltas(contrasts)
    nonzero = int(np.count_nonzero(deltas))
    if not deltas.size or not nonzero:
        return WilcoxonResult(
            StatisticalTestId.WILCOXON_SIGNED_RANK,
            "two-sided",
            "pratt",
            "unavailable",
            None,
            None,
            nonzero,
            AvailabilityStatus.UNDEFINED,
            "Wilcoxon requires a nonzero paired difference",
        )
    values = _wilcoxon_values(stats.wilcoxon(deltas, alternative="two-sided", zero_method="pratt", method="asymptotic"))
    if values is None:
        return WilcoxonResult(
            StatisticalTestId.WILCOXON_SIGNED_RANK,
            "two-sided",
            "pratt",
            "scipy_asymptotic",
            None,
            None,
            nonzero,
            AvailabilityStatus.UNAVAILABLE,
            "SciPy Wilcoxon result does not expose statistic and p-value",
        )
    return WilcoxonResult(
        StatisticalTestId.WILCOXON_SIGNED_RANK,
        "two-sided",
        "pratt",
        "scipy_asymptotic",
        values[0],
        values[1],
        nonzero,
        AvailabilityStatus.AVAILABLE,
        "",
    )


def matched_pairs_rank_biserial(
    contrasts: tuple,
) -> RankBiserialResult:
    deltas = _deltas(contrasts)
    nonzero = deltas[deltas != 0]
    if not nonzero.size:
        return RankBiserialResult(
            EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL,
            None,
            None,
            None,
            0,
            AvailabilityStatus.UNDEFINED,
            "rank-biserial correlation requires a nonzero paired difference",
        )
    ranks = stats.rankdata(np.abs(nonzero), method="average")
    positive = float(np.sum(ranks[nonzero > 0]))
    negative = float(np.sum(ranks[nonzero < 0]))
    return RankBiserialResult(
        EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL,
        (positive - negative) / (positive + negative),
        positive,
        negative,
        int(nonzero.size),
        AvailabilityStatus.AVAILABLE,
        "",
    )


def holm_adjust(raw_p_values: tuple[float, ...], *, family_name: str, alpha: Ratio) -> MultiplicityResult:
    if not family_name or not raw_p_values:
        raise ValueError("Holm correction requires a predeclared non-empty family")
    if any(not isfinite(value) or not 0 <= value <= 1 for value in raw_p_values):
        raise ValueError("raw p-values must be finite values in [0, 1]")
    rejected, adjusted, _, _ = multipletests(
        raw_p_values, alpha=alpha.value, method="holm", is_sorted=False, returnsorted=False
    )
    return MultiplicityResult(
        MultiplicityCorrectionId.HOLM,
        family_name,
        raw_p_values,
        tuple(float(value) for value in adjusted),
        tuple(bool(value) for value in rejected),
    )


def sign_consistency(
    contrasts: tuple,
) -> PairedDifferenceCounts:
    return count_paired_differences(tuple(item.delta.value for item in contrasts))


def _wilcoxon_values(result: object) -> tuple[float, float] | None:
    statistic = getattr(result, "statistic", None)
    p_value = getattr(result, "pvalue", None)
    if not isinstance(statistic, int | float) or not isinstance(p_value, int | float):
        return None
    return float(statistic), float(p_value)
