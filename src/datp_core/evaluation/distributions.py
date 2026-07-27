"""Per-client score distributions and threshold trade-offs."""

from __future__ import annotations

import polars as pl

from datp_core.core.identifiers import ClientId
from datp_core.evaluation.enums import MetricStatus
from datp_core.evaluation.models import (
    CdfPoint,
    ClientScoreDistribution,
    MetricValue,
    ThresholdPosition,
    ThresholdTradeoff,
)

_REQUIRED_METRIC_COLUMNS: tuple[str, ...] = (
    "client_id",
    "false_positive_rate",
    "false_positive_rate_status",
    "true_positive_rate",
    "true_positive_rate_status",
    "balanced_accuracy",
    "balanced_accuracy_status",
    "macro_f1",
    "macro_f1_status",
)


def _validate_distribution_inputs(
    thresholds: pl.DataFrame, metrics: pl.DataFrame, scores: pl.DataFrame
) -> None:
    for col in ("client_id", "threshold"):
        if col not in thresholds.columns:
            raise ValueError(f"Thresholds missing column: {col}")
    for col in _REQUIRED_METRIC_COLUMNS:
        if col not in metrics.columns:
            raise ValueError(f"Metrics missing column: {col}")
    for col in ("client_id", "score", "label"):
        if col not in scores.columns:
            raise ValueError(f"Scores missing column: {col}")
    if thresholds["client_id"].is_duplicated().any():
        raise ValueError("Duplicate client_id in thresholds")
    if metrics["client_id"].is_duplicated().any():
        raise ValueError("Duplicate client_id in metrics")


def _build_metric_value(val: object, status_str: str) -> MetricValue:
    status = MetricStatus(status_str)
    if val is None:
        return MetricValue.unavailable(status)
    if isinstance(val, (int, float)):
        return MetricValue(value=float(val), status=status)
    return MetricValue.unavailable(MetricStatus.FAILED_INVALID_ARTIFACT)


def _empirical_cdf(values: list[float]) -> tuple[CdfPoint, ...]:
    return tuple(
        CdfPoint(score=value, cumulative_probability=(index + 1) / len(values))
        for index, value in enumerate(values)
    )


def _cdf_position(values: list[float], threshold: float) -> float | None:
    return sum(value <= threshold for value in values) / len(values) if values else None


def client_score_distributions(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    scores: pl.DataFrame,
    client_filter: ClientId | None,
) -> tuple[ClientScoreDistribution, ...]:
    _validate_distribution_inputs(thresholds, metrics, scores)

    client_ids = sorted(str(c) for c in thresholds["client_id"].unique().to_list())
    if client_filter is not None:
        filter_str = str(client_filter)
        if filter_str not in client_ids:
            raise ValueError(f"Locked client '{filter_str}' is unavailable in this evaluation")
        client_ids = [filter_str]

    thresholds_filtered = thresholds.filter(pl.col("client_id").is_in(client_ids))
    metrics_filtered = metrics.filter(pl.col("client_id").is_in(client_ids))

    missing_threshold = set(client_ids) - set(str(c) for c in thresholds_filtered["client_id"].to_list())
    if missing_threshold:
        raise ValueError(f"Missing threshold rows for clients: {missing_threshold}")
    missing_metric = set(client_ids) - set(str(c) for c in metrics_filtered["client_id"].to_list())
    if missing_metric:
        raise ValueError(f"Missing metric rows for clients: {missing_metric}")

    threshold_map: dict[str, float] = dict(
        zip(
            (str(c) for c in thresholds_filtered["client_id"].to_list()),
            (float(t) for t in thresholds_filtered["threshold"].to_list()),
            strict=True,
        )
    )

    result: list[ClientScoreDistribution] = []
    for client in client_ids:
        client_scores = scores.filter(pl.col("client_id") == client)
        benign = (
            client_scores.filter(pl.col("label") == 0)
            .select(pl.col("score").sort())
            .to_series()
            .to_list()
        )
        attack = (
            client_scores.filter(pl.col("label") == 1)
            .select(pl.col("score").sort())
            .to_series()
            .to_list()
        )

        metric_row = metrics_filtered.filter(pl.col("client_id") == client).row(0, named=True)

        result.append(
            ClientScoreDistribution(
                client_id=ClientId(client),
                benign_score_cdf=_empirical_cdf(benign),
                attack_score_cdf=_empirical_cdf(attack),
                threshold_position=ThresholdPosition(
                    threshold=threshold_map[client],
                    benign_cdf=_cdf_position(benign, threshold_map[client]),
                    attack_cdf=_cdf_position(attack, threshold_map[client]),
                ),
                threshold=threshold_map[client],
                false_positive_rate=_build_metric_value(
                    metric_row["false_positive_rate"], str(metric_row["false_positive_rate_status"])
                ),
                true_positive_rate=_build_metric_value(
                    metric_row["true_positive_rate"], str(metric_row["true_positive_rate_status"])
                ),
                balanced_accuracy=_build_metric_value(
                    metric_row["balanced_accuracy"], str(metric_row["balanced_accuracy_status"])
                ),
                macro_f1=_build_metric_value(
                    metric_row["macro_f1"], str(metric_row["macro_f1_status"])
                ),
            )
        )

    return tuple(result)


def threshold_tradeoff(
    baseline: tuple[ClientScoreDistribution, ...],
    shifted: tuple[ClientScoreDistribution, ...],
) -> tuple[ThresholdTradeoff, ...]:
    baseline_by_id = {d.client_id: d for d in baseline}
    shifted_by_id = {d.client_id: d for d in shifted}
    if set(baseline_by_id) != set(shifted_by_id):
        raise ValueError("Threshold trade-off sources have incompatible client populations")
    return tuple(
        ThresholdTradeoff(
            client_id=client_id,
            threshold_shift=shifted_by_id[client_id].threshold - baseline_by_id[client_id].threshold,
            fpr_delta=_metric_delta(
                baseline_by_id[client_id].false_positive_rate, shifted_by_id[client_id].false_positive_rate
            ),
            tpr_delta=_metric_delta(
                baseline_by_id[client_id].true_positive_rate, shifted_by_id[client_id].true_positive_rate
            ),
        )
        for client_id in sorted(baseline_by_id)
    )


def _metric_delta(baseline: MetricValue | None, shifted: MetricValue | None) -> float | None:
    if baseline is None or shifted is None:
        return None
    if baseline.value is None or shifted.value is None:
        return None
    return shifted.value - baseline.value
