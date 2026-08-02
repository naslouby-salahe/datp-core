"""Wilcoxon, rank-biserial correlation, Holm correction, and sign consistency."""

from math import isfinite
from numbers import Real

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

from datp_core.analysis.descriptive import count_paired_differences
from datp_core.analysis.inference.bootstrap import contrast_deltas
from datp_core.analysis.models import (
    MultiplicityDecision,
    MultiplicityResult,
    PairedContrasts,
    PairedDifferenceCounts,
    PValue,
    RankBiserialResult,
    WilcoxonComputationMethod,
    WilcoxonResult,
)
from datp_core.domain.enums import (
    AvailabilityStatus,
    MultiplicityCorrectionId,
)
from datp_core.domain.values import Ratio


def paired_wilcoxon(
    contrasts: PairedContrasts,
) -> WilcoxonResult:
    deltas = contrast_deltas(contrasts)
    nonzero_pair_count = int(np.count_nonzero(deltas))
    if not deltas.size or not nonzero_pair_count:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=None,
            availability=AvailabilityStatus.UNDEFINED,
            reason=("Wilcoxon requires at least one nonzero paired difference"),
        )

    values = _wilcoxon_values(
        stats.wilcoxon(
            deltas,
            alternative="two-sided",
            zero_method="pratt",
            method="asymptotic",
        )
    )
    if values is None:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=(WilcoxonComputationMethod.SCIPY_ASYMPTOTIC),
            availability=AvailabilityStatus.UNAVAILABLE,
            reason=("SciPy Wilcoxon result does not expose finite statistic and p-value values"),
        )

    statistic, p_value = values
    return WilcoxonResult(
        statistic=statistic,
        p_value=PValue(p_value),
        nonzero_pair_count=nonzero_pair_count,
        computation_method=(WilcoxonComputationMethod.SCIPY_ASYMPTOTIC),
        availability=AvailabilityStatus.AVAILABLE,
        reason="",
    )


def matched_pairs_rank_biserial(
    contrasts: PairedContrasts,
) -> RankBiserialResult:
    deltas = contrast_deltas(contrasts)
    nonzero = deltas[deltas != 0.0]
    if not nonzero.size:
        return RankBiserialResult(
            value=None,
            positive_rank_sum=None,
            negative_rank_sum=None,
            nonzero_pair_count=0,
            availability=AvailabilityStatus.UNDEFINED,
            reason=("rank-biserial correlation requires at least one nonzero paired difference"),
        )

    ranks = stats.rankdata(
        np.abs(nonzero),
        method="average",
    )
    positive_rank_sum = float(np.sum(ranks[nonzero > 0.0]))
    negative_rank_sum = float(np.sum(ranks[nonzero < 0.0]))
    total_rank_sum = positive_rank_sum + negative_rank_sum
    return RankBiserialResult(
        value=(positive_rank_sum - negative_rank_sum) / total_rank_sum,
        positive_rank_sum=positive_rank_sum,
        negative_rank_sum=negative_rank_sum,
        nonzero_pair_count=int(nonzero.size),
        availability=AvailabilityStatus.AVAILABLE,
        reason="",
    )


def holm_adjust(
    raw_p_values: tuple[float, ...],
    *,
    family_name: str,
    alpha: Ratio,
) -> MultiplicityResult:
    if not family_name.strip() or not raw_p_values:
        raise ValueError("Holm correction requires a named non-empty test family")
    if any(not isfinite(value) or not 0.0 <= value <= 1.0 for value in raw_p_values):
        raise ValueError("raw p-values must be finite and lie in [0, 1]")

    rejected, adjusted, _, _ = multipletests(
        raw_p_values,
        alpha=alpha.value,
        method="holm",
        is_sorted=False,
        returnsorted=False,
    )
    decisions = tuple(
        MultiplicityDecision(
            raw_p_value=PValue(raw),
            adjusted_p_value=PValue(float(corrected)),
            rejected=bool(is_rejected),
        )
        for raw, corrected, is_rejected in zip(
            raw_p_values,
            adjusted,
            rejected,
            strict=True,
        )
    )
    return MultiplicityResult(
        correction=MultiplicityCorrectionId.HOLM,
        family_name=family_name,
        decisions=decisions,
    )


def sign_consistency(
    contrasts: PairedContrasts,
) -> PairedDifferenceCounts:
    return count_paired_differences(tuple(contrast.delta for contrast in contrasts))


def _wilcoxon_values(
    result: object,
) -> tuple[float, float] | None:
    statistic = getattr(result, "statistic", None)
    p_value = getattr(result, "pvalue", None)
    if not _is_finite_real(statistic) or not _is_finite_real(p_value):
        return None
    return float(statistic), float(p_value)


def _is_finite_real(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(float(value))
