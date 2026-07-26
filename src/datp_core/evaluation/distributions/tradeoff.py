"""Threshold tradeoff calculation."""

from __future__ import annotations

from collections.abc import Mapping

from datp_core.evaluation.distributions.models import (
    ClientScoreDistributionRecord,
    ThresholdTradeoffEntry,
)


def threshold_tradeoff(
    baseline: Mapping[str, ClientScoreDistributionRecord], shifted: Mapping[str, ClientScoreDistributionRecord]
) -> dict[str, ThresholdTradeoffEntry]:
    if set(baseline) != set(shifted):
        raise ValueError("Threshold trade-off sources have incompatible client populations")
    return {
        client: ThresholdTradeoffEntry(
            threshold_shift=shifted[client].threshold - baseline[client].threshold,
            fpr_delta=_metric_delta(baseline[client].false_positive_rate,
                                    shifted[client].false_positive_rate),
            tpr_delta=_metric_delta(baseline[client].true_positive_rate,
                                    shifted[client].true_positive_rate),
        )
        for client in sorted(baseline)
    }


def _metric_delta(baseline: float | None, shifted: float | None) -> float | None:
    return shifted - baseline if isinstance(baseline, float) and isinstance(shifted, float) else None
