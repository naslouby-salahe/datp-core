"""Wilcoxon, rank-biserial correlation, Holm correction, and sign consistency."""

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

from datp_core.analysis.inference.bootstrap import contrast_deltas
from datp_core.analysis.models import (
    MultiplicityDecision,
    MultiplicityResult,
    PairedContrasts,
    PValue,
    RankBiserialResult,
    WilcoxonComputationMethod,
    WilcoxonResult,
    _extract_named_attributes,
)
from datp_core.domain.enums import (
    AvailabilityStatus,
    MultiplicityCorrectionId,
)
from datp_core.domain.values import Ratio


def paired_wilcoxon(contrasts: PairedContrasts) -> WilcoxonResult:
    deltas = contrast_deltas(contrasts)
    nonzero_pair_count = int(np.count_nonzero(deltas))

    if not nonzero_pair_count:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=None,
            availability=AvailabilityStatus.UNDEFINED,
            reason="Wilcoxon requires at least one nonzero paired difference",
        )

    res = stats.wilcoxon(
        deltas,
        alternative="two-sided",
        zero_method="pratt",
        method="asymptotic",
    )

    extracted = _extract_named_attributes(res, ("statistic", "pvalue"))
    if extracted is None:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=WilcoxonComputationMethod.SCIPY_ASYMPTOTIC,
            availability=AvailabilityStatus.UNAVAILABLE,
            reason="SciPy Wilcoxon result does not expose finite statistic and p-value values",
        )

    statistic_val, pvalue_val = extracted
    return WilcoxonResult(
        statistic=statistic_val,
        p_value=PValue(value=pvalue_val),
        nonzero_pair_count=nonzero_pair_count,
        computation_method=WilcoxonComputationMethod.SCIPY_ASYMPTOTIC,
        availability=AvailabilityStatus.AVAILABLE,
        reason="",
    )


def matched_pairs_rank_biserial(contrasts: PairedContrasts) -> RankBiserialResult:
    deltas = contrast_deltas(contrasts)
    nonzero = deltas[deltas != 0.0]

    if not nonzero.size:
        return RankBiserialResult(
            value=None,
            positive_rank_sum=None,
            negative_rank_sum=None,
            nonzero_pair_count=0,
            availability=AvailabilityStatus.UNDEFINED,
            reason="rank-biserial correlation requires at least one nonzero paired difference",
        )

    ranks = stats.rankdata(np.abs(nonzero), method="average")
    pos_mask = nonzero > 0.0
    positive_rank_sum = float(np.sum(ranks[pos_mask]))
    negative_rank_sum = float(np.sum(ranks[~pos_mask]))
    rank_total = float(ranks.sum())

    return RankBiserialResult(
        value=(positive_rank_sum - negative_rank_sum) / rank_total,
        positive_rank_sum=positive_rank_sum,
        negative_rank_sum=negative_rank_sum,
        nonzero_pair_count=nonzero.size,
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

    raw_pvs = tuple(PValue(value=v) for v in raw_p_values)
    rejected, adjusted, _, _ = multipletests(
        tuple(pv.value for pv in raw_pvs),
        alpha=alpha.value,
        method="holm",
        is_sorted=False,
        returnsorted=False,
    )

    decisions = tuple(
        MultiplicityDecision(
            raw_p_value=raw_pvs[i],
            adjusted_p_value=PValue(value=float(corrected)),
            rejected=bool(is_rejected),
        )
        for i, (corrected, is_rejected) in enumerate(zip(adjusted, rejected, strict=True))
    )

    return MultiplicityResult(
        correction=MultiplicityCorrectionId.HOLM,
        family_name=family_name,
        decisions=decisions,
    )
