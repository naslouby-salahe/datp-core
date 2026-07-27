"""Per-client empirical CDF and threshold position."""

from __future__ import annotations

import polars as pl

from datp_core.evaluation.distributions.models import (
    CdfPoint,
    ClientScoreDistributionRecord,
    ThresholdPositionRecord,
)


def client_score_distributions(
    thresholds: pl.DataFrame, metrics: pl.DataFrame, scores: pl.DataFrame, client_filter: str | None
) -> dict[str, ClientScoreDistributionRecord]:
    # Polars unique before Python bridge
    clients = {str(client) for client in thresholds["client_id"].unique().to_list()}
    if client_filter is not None:
        if client_filter not in clients:
            raise ValueError(f"Locked client '{client_filter}' is unavailable in this evaluation")
        clients = {client_filter}
    # Column-based access instead of row iteration
    _thresh = thresholds.select("client_id", "threshold").to_dict(as_series=False)
    threshold_by_client = {str(c): float(v) for c, v in zip(_thresh["client_id"], _thresh["threshold"], strict=False)}
    metrics_by_client = {str(row["client_id"]): row for row in metrics.to_dicts()}
    result: dict[str, ClientScoreDistributionRecord] = {}
    for client in sorted(clients):
        metric = metrics_by_client.get(client)
        if metric is None:
            raise ValueError(f"Score distribution metric is unavailable for client '{client}'")
        client_scores = scores.filter(pl.col("client_id") == client)
        threshold = threshold_by_client[client]
        # Polars sort before Python bridge
        benign = client_scores.filter(pl.col("label") == 0).select(pl.col("score").sort()).to_series().to_list()
        attack = client_scores.filter(pl.col("label") == 1).select(pl.col("score").sort()).to_series().to_list()
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
