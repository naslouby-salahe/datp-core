"""Paired contrasts, non-parametric inference, and multiplicity."""

import numpy as np
from numpy.typing import NDArray
from scipy import stats
from statsmodels.stats.multitest import multipletests

from datp_core.analysis.models import (
    CorrelationCoefficient,
    MultiplicityDecision,
    MultiplicityPlan,
    MultiplicityResult,
    PairedContrasts,
    PValue,
    RankBiserialResult,
    WilcoxonComputationMethod,
    WilcoxonResult,
    extract_named_numeric_attributes,
)
from datp_core.domain.enums import AvailabilityStatus, EffectSizeId, StatisticalTestId
from datp_core.domain.values import PairedObservationCount, RankSum
from datp_core.protocols.statistics import PairedInferenceProtocol


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
    result = stats.wilcoxon(
        deltas,
        alternative=protocol.wilcoxon_alternative.value,
        zero_method=protocol.wilcoxon_zero_method.value,
        method=protocol.wilcoxon_computation_method.value,
    )
    extracted = extract_named_numeric_attributes(result, ("statistic", "pvalue"))
    if extracted is None:
        return WilcoxonResult(
            statistic=None,
            p_value=None,
            nonzero_pair_count=nonzero_pair_count,
            computation_method=WilcoxonComputationMethod.SCIPY_ASYMPTOTIC,
            availability=AvailabilityStatus.UNAVAILABLE,
            reason="SciPy Wilcoxon result does not expose finite statistic and p-value values",
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
            reason="rank-biserial correlation requires at least one nonzero paired difference",
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


def holm_adjust(plan: MultiplicityPlan, protocol: PairedInferenceProtocol) -> MultiplicityResult:
    rejected, adjusted, _, _ = multipletests(
        tuple(value.value for value in plan.raw_p_values),
        alpha=plan.alpha.value,
        method=protocol.multiplicity_correction.value,
        is_sorted=False,
        returnsorted=False,
    )
    return MultiplicityResult(
        correction=protocol.multiplicity_correction,
        family_name=plan.family_name,
        decisions=tuple(
            MultiplicityDecision(
                raw_p_value=raw,
                adjusted_p_value=PValue(float(corrected)),
                rejected=bool(is_rejected),
            )
            for raw, corrected, is_rejected in zip(
                plan.raw_p_values,
                adjusted,
                rejected,
                strict=True,
            )
        ),
    )
