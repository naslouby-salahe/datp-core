"""Per-client score distributions and threshold trade-offs."""

from __future__ import annotations

from collections.abc import Sequence
from numbers import Real

import polars as pl

from datp_core.core.identifiers import ClientId
from datp_core.evaluation.enums import (
    EvaluationColumn,
    MetricStatus,
)
from datp_core.evaluation.models import (
    CdfPoint,
    ClientScoreDistribution,
    MetricValue,
    ThresholdPosition,
    ThresholdTradeoff,
)


_METRIC_COLUMNS = (
    EvaluationColumn.FALSE_POSITIVE_RATE,
    EvaluationColumn.FALSE_POSITIVE_RATE_STATUS,
    EvaluationColumn.TRUE_POSITIVE_RATE,
    EvaluationColumn.TRUE_POSITIVE_RATE_STATUS,
    EvaluationColumn.BALANCED_ACCURACY,
    EvaluationColumn.BALANCED_ACCURACY_STATUS,
    EvaluationColumn.MACRO_F1,
    EvaluationColumn.MACRO_F1_STATUS,
)


def _normalize_inputs(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    scores: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    threshold_required = (
        EvaluationColumn.CLIENT_ID,
        EvaluationColumn.THRESHOLD,
    )

    metric_required = (
        EvaluationColumn.CLIENT_ID,
        *_METRIC_COLUMNS,
    )

    score_required = (
        EvaluationColumn.CLIENT_ID,
        EvaluationColumn.SCORE,
        EvaluationColumn.LABEL,
    )

    for label, frame, required in (
        ("Thresholds", thresholds, threshold_required),
        ("Metrics", metrics, metric_required),
        ("Scores", scores, score_required),
    ):
        missing = tuple(
            column
            for column in required
            if column not in frame.columns
        )

        if missing:
            raise ValueError(
                f"{label} missing columns: "
                f"{[column.value for column in missing]}"
            )

    normalized_thresholds = thresholds.select(
        pl.col(EvaluationColumn.CLIENT_ID).cast(
            pl.String,
            strict=True,
        ),
        pl.col(EvaluationColumn.THRESHOLD).cast(
            pl.Float64,
            strict=True,
        ),
    )

    normalized_metrics = metrics.select(
        pl.col(EvaluationColumn.CLIENT_ID).cast(
            pl.String,
            strict=True,
        ),
        *(pl.col(column) for column in _METRIC_COLUMNS),
    )

    normalized_scores = scores.select(
        pl.col(EvaluationColumn.CLIENT_ID).cast(
            pl.String,
            strict=True,
        ),
        pl.col(EvaluationColumn.SCORE).cast(
            pl.Float64,
            strict=True,
        ),
        pl.col(EvaluationColumn.LABEL).cast(
            pl.Int8,
            strict=True,
        ),
    )

    if normalized_thresholds.get_column(
        EvaluationColumn.CLIENT_ID
    ).is_null().any():
        raise ValueError(
            "Threshold client IDs must not be null"
        )

    if normalized_metrics.get_column(
        EvaluationColumn.CLIENT_ID
    ).is_null().any():
        raise ValueError(
            "Metric client IDs must not be null"
        )

    if normalized_scores.get_column(
        EvaluationColumn.CLIENT_ID
    ).is_null().any():
        raise ValueError(
            "Score client IDs must not be null"
        )

    if normalized_thresholds.get_column(
        EvaluationColumn.CLIENT_ID
    ).is_duplicated().any():
        raise ValueError(
            "Threshold client IDs must be unique"
        )

    if normalized_metrics.get_column(
        EvaluationColumn.CLIENT_ID
    ).is_duplicated().any():
        raise ValueError(
            "Metric client IDs must be unique"
        )

    threshold_values = normalized_thresholds.get_column(
        EvaluationColumn.THRESHOLD
    )

    score_values = normalized_scores.get_column(
        EvaluationColumn.SCORE
    )

    if (
        threshold_values.is_null().any()
        or threshold_values.is_nan().any()
        or threshold_values.is_infinite().any()
    ):
        raise ValueError(
            "Distribution thresholds must be finite and non-null"
        )

    if (
        score_values.is_null().any()
        or score_values.is_nan().any()
        or score_values.is_infinite().any()
    ):
        raise ValueError("Distribution scores must be finite")

    labels = normalized_scores.get_column(
        EvaluationColumn.LABEL
    )

    if labels.is_null().any() or not labels.is_in((0, 1)).all():
        raise ValueError(
            "Distribution labels must be binary and non-null"
        )

    return (
        normalized_thresholds,
        normalized_metrics,
        normalized_scores,
    )


def _metric_value(
    value: object,
    status_value: object,
) -> MetricValue:
    status = MetricStatus(str(status_value))

    if value is None:
        return MetricValue.unavailable(status)

    if not isinstance(value, Real):
        raise ValueError(
            "Metric value must be numeric or null, "
            f"got {type(value).__name__}"
        )

    numeric = float(value)

    if status is MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR:
        return MetricValue.warning(numeric, status)

    return MetricValue(
        value=numeric,
        status=status,
    )


def _empirical_cdf(
    values: Sequence[float],
) -> tuple[CdfPoint, ...]:
    count = len(values)

    return tuple(
        CdfPoint(
            score=value,
            cumulative_probability=(index + 1) / count,
        )
        for index, value in enumerate(values)
    )


def _cdf_position(
    values: Sequence[float],
    threshold: float,
) -> float | None:
    if not values:
        return None

    return (
        sum(value <= threshold for value in values)
        / len(values)
    )


def client_score_distributions(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    scores: pl.DataFrame,
    client_filter: ClientId | None,
) -> tuple[ClientScoreDistribution, ...]:
    thresholds, metrics, scores = _normalize_inputs(
        thresholds,
        metrics,
        scores,
    )

    selected_clients = thresholds.select(
        EvaluationColumn.CLIENT_ID
    )

    if client_filter is not None:
        selected_clients = selected_clients.filter(
            pl.col(EvaluationColumn.CLIENT_ID)
            == str(client_filter)
        )

        if selected_clients.is_empty():
            raise ValueError(
                f"Locked client '{client_filter}' "
                "is unavailable in this evaluation"
            )

    missing_metrics = selected_clients.join(
        metrics.select(EvaluationColumn.CLIENT_ID),
        on=EvaluationColumn.CLIENT_ID,
        how="anti",
    )

    if not missing_metrics.is_empty():
        raise ValueError(
            "Missing metric rows: "
            f"{tuple(missing_metrics.iter_rows(named=False))}"
        )

    score_groups = (
        scores.join(
            selected_clients,
            on=EvaluationColumn.CLIENT_ID,
            how="inner",
            validate="m:1",
        )
        .group_by(EvaluationColumn.CLIENT_ID)
        .agg(
            pl.col(EvaluationColumn.SCORE)
            .filter(pl.col(EvaluationColumn.LABEL) == 0)
            .sort()
            .alias("_benign_scores"),
            pl.col(EvaluationColumn.SCORE)
            .filter(pl.col(EvaluationColumn.LABEL) == 1)
            .sort()
            .alias("_attack_scores"),
        )
    )

    missing_scores = selected_clients.join(
        score_groups.select(EvaluationColumn.CLIENT_ID),
        on=EvaluationColumn.CLIENT_ID,
        how="anti",
    )

    if not missing_scores.is_empty():
        raise ValueError(
            "Missing score rows: "
            f"{tuple(missing_scores.iter_rows(named=False))}"
        )

    assembled = (
        selected_clients
        .join(
            thresholds,
            on=EvaluationColumn.CLIENT_ID,
            how="inner",
            validate="1:1",
        )
        .join(
            metrics,
            on=EvaluationColumn.CLIENT_ID,
            how="inner",
            validate="1:1",
        )
        .join(
            score_groups,
            on=EvaluationColumn.CLIENT_ID,
            how="inner",
            validate="1:1",
        )
        .select(
            EvaluationColumn.CLIENT_ID,
            EvaluationColumn.THRESHOLD,
            *_METRIC_COLUMNS,
            "_benign_scores",
            "_attack_scores",
        )
        .sort(EvaluationColumn.CLIENT_ID)
    )

    result: list[ClientScoreDistribution] = []

    for row in assembled.iter_rows(named=False):
        (
            client_raw,
            threshold_raw,
            fpr_raw,
            fpr_status_raw,
            tpr_raw,
            tpr_status_raw,
            balanced_accuracy_raw,
            balanced_accuracy_status_raw,
            macro_f1_raw,
            macro_f1_status_raw,
            benign_raw,
            attack_raw,
        ) = row

        threshold = float(threshold_raw)
        benign = tuple(float(value) for value in benign_raw)
        attack = tuple(float(value) for value in attack_raw)

        result.append(
            ClientScoreDistribution(
                client_id=ClientId(str(client_raw)),
                benign_score_cdf=_empirical_cdf(benign),
                attack_score_cdf=_empirical_cdf(attack),
                threshold_position=ThresholdPosition(
                    threshold=threshold,
                    benign_cdf=_cdf_position(
                        benign,
                        threshold,
                    ),
                    attack_cdf=_cdf_position(
                        attack,
                        threshold,
                    ),
                ),
                threshold=threshold,
                false_positive_rate=_metric_value(
                    fpr_raw,
                    fpr_status_raw,
                ),
                true_positive_rate=_metric_value(
                    tpr_raw,
                    tpr_status_raw,
                ),
                balanced_accuracy=_metric_value(
                    balanced_accuracy_raw,
                    balanced_accuracy_status_raw,
                ),
                macro_f1=_metric_value(
                    macro_f1_raw,
                    macro_f1_status_raw,
                ),
            )
        )

    return tuple(result)


def threshold_tradeoff(
    baseline: tuple[ClientScoreDistribution, ...],
    shifted: tuple[ClientScoreDistribution, ...],
) -> tuple[ThresholdTradeoff, ...]:
    baseline_sorted = tuple(
        sorted(
            baseline,
            key=lambda item: item.client_id,
        )
    )

    shifted_sorted = tuple(
        sorted(
            shifted,
            key=lambda item: item.client_id,
        )
    )

    baseline_ids = tuple(
        item.client_id
        for item in baseline_sorted
    )

    shifted_ids = tuple(
        item.client_id
        for item in shifted_sorted
    )

    if baseline_ids != shifted_ids:
        raise ValueError(
            "Threshold trade-off sources have "
            "incompatible client populations"
        )

    return tuple(
        ThresholdTradeoff(
            client_id=baseline_item.client_id,
            threshold_shift=(
                shifted_item.threshold
                - baseline_item.threshold
            ),
            fpr_delta=_metric_delta(
                baseline_item.false_positive_rate,
                shifted_item.false_positive_rate,
            ),
            tpr_delta=_metric_delta(
                baseline_item.true_positive_rate,
                shifted_item.true_positive_rate,
            ),
        )
        for baseline_item, shifted_item in zip(
            baseline_sorted,
            shifted_sorted,
            strict=True,
        )
    )


def _metric_delta(
    baseline: MetricValue,
    shifted: MetricValue,
) -> float | None:
    if baseline.value is None or shifted.value is None:
        return None

    return shifted.value - baseline.value