"""Per-client score-distribution and threshold-tradeoff views over immutable evaluation artifacts.

Used by analysis-family functions that need typed CDF/threshold-position summaries rather than
recomputing them from raw score frames themselves.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class CdfPoint:
    score: float
    cumulative_probability: float


@define(frozen=True, slots=True, kw_only=True)
class ThresholdPositionRecord:
    threshold: float
    benign_cdf: float | None
    attack_cdf: float | None


@define(frozen=True, slots=True, kw_only=True)
class ClientScoreDistributionRecord:
    per_client_benign_score_cdf: tuple[CdfPoint, ...]
    per_client_attack_score_cdf: tuple[CdfPoint, ...]
    per_client_threshold_position: ThresholdPositionRecord
    threshold: float
    false_positive_rate: float | None
    false_positive_rate_status: str
    true_positive_rate: float | None
    true_positive_rate_status: str
    balanced_accuracy: float | None
    balanced_accuracy_status: str
    macro_f1: float | None
    macro_f1_status: str


@define(frozen=True, slots=True, kw_only=True)
class ThresholdTradeoffEntry:
    threshold_shift: float
    fpr_delta: float | None
    tpr_delta: float | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileVarianceTerms:
    within_term: float
    between_term: float
    between_ratio: float | None


def client_score_distributions(
    thresholds: pl.DataFrame, metrics: pl.DataFrame, scores: pl.DataFrame, client_filter: str | None
) -> dict[str, ClientScoreDistributionRecord]:
    clients = {str(client) for client in thresholds["client_id"].to_list()}
    if client_filter is not None:
        if client_filter not in clients:
            raise ValueError(f"Locked client '{client_filter}' is unavailable in this evaluation")
        clients = {client_filter}
    threshold_by_client = {
        str(client): float(value) for client, value in thresholds.select("client_id", "threshold").iter_rows()
    }
    metrics_by_client = {str(row["client_id"]): row for row in metrics.to_dicts()}
    result: dict[str, ClientScoreDistributionRecord] = {}
    for client in sorted(clients):
        metric = metrics_by_client.get(client)
        if metric is None:
            raise ValueError(f"Score distribution metric is unavailable for client '{client}'")
        client_scores = scores.filter(pl.col("client_id") == client)
        threshold = threshold_by_client[client]
        benign = sorted(float(value) for value in client_scores.filter(pl.col("label") == 0)["score"].to_list())
        attack = sorted(float(value) for value in client_scores.filter(pl.col("label") == 1)["score"].to_list())
        result[client] = ClientScoreDistributionRecord(
            per_client_benign_score_cdf=_empirical_cdf(benign),
            per_client_attack_score_cdf=_empirical_cdf(attack),
            per_client_threshold_position=ThresholdPositionRecord(
                threshold=threshold,
                benign_cdf=_cdf_position(benign, threshold),
                attack_cdf=_cdf_position(attack, threshold),
            ),
            threshold=threshold,
            false_positive_rate=metric["false_positive_rate"],
            false_positive_rate_status=metric["false_positive_rate_status"],
            true_positive_rate=metric["true_positive_rate"],
            true_positive_rate_status=metric["true_positive_rate_status"],
            balanced_accuracy=metric["balanced_accuracy"],
            balanced_accuracy_status=metric["balanced_accuracy_status"],
            macro_f1=metric["macro_f1"],
            macro_f1_status=metric["macro_f1_status"],
        )
    return result


def _empirical_cdf(values: list[float]) -> tuple[CdfPoint, ...]:
    return tuple(
        CdfPoint(score=value, cumulative_probability=(index + 1) / len(values)) for index, value in enumerate(values)
    )


def _cdf_position(values: list[float], threshold: float) -> float | None:
    return sum(value <= threshold for value in values) / len(values) if values else None


def threshold_tradeoff(
    baseline: dict[str, ClientScoreDistributionRecord], shifted: dict[str, ClientScoreDistributionRecord]
) -> dict[str, ThresholdTradeoffEntry]:
    if set(baseline) != set(shifted):
        raise ValueError("Threshold trade-off sources have incompatible client populations")
    return {
        client: ThresholdTradeoffEntry(
            threshold_shift=shifted[client].threshold - baseline[client].threshold,
            fpr_delta=_metric_delta(baseline[client].false_positive_rate, shifted[client].false_positive_rate),
            tpr_delta=_metric_delta(baseline[client].true_positive_rate, shifted[client].true_positive_rate),
        )
        for client in sorted(baseline)
    }


def _metric_delta(baseline: float | None, shifted: float | None) -> float | None:
    return shifted - baseline if isinstance(baseline, float) and isinstance(shifted, float) else None


def calibration_variance_terms(calibration: pl.DataFrame) -> QuantileVarianceTerms:
    values = np.asarray(calibration["score"].to_list(), dtype=np.float64)
    if values.size == 0:
        raise ValueError("Quantile-estimation analysis requires calibration scores")
    pooled_variance = float(np.var(values))
    means_and_variances: list[tuple[int, float, float]] = []
    for _, group in calibration.group_by("client_id", maintain_order=True):
        group_values = np.asarray(group["score"].to_list(), dtype=np.float64)
        means_and_variances.append((group_values.size, float(group_values.mean()), float(np.var(group_values))))
    total = sum(count for count, _, _ in means_and_variances)
    pooled_mean = float(values.mean())
    within = sum(count * variance for count, _, variance in means_and_variances) / total
    between = sum(count * (mean - pooled_mean) ** 2 for count, mean, _ in means_and_variances) / total
    return QuantileVarianceTerms(
        within_term=within,
        between_term=between,
        between_ratio=between / pooled_variance if pooled_variance else None,
    )


__all__ = [
    "CdfPoint",
    "ClientScoreDistributionRecord",
    "QuantileVarianceTerms",
    "ThresholdPositionRecord",
    "ThresholdTradeoffEntry",
    "calibration_variance_terms",
    "client_score_distributions",
    "threshold_tradeoff",
]
