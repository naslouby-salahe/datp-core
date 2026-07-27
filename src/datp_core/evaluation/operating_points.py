"""Per-client operating-point and AUROC evaluation."""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.metrics import roc_auc_score

from datp_core.evaluation.enums import (
    EvaluationColumn,
    MetricStatus,
    MissingThresholdPolicy,
)

_RESULT_FIELDS = (
    (EvaluationColumn.CLIENT_ID, pl.String),
    (EvaluationColumn.TRUE_POSITIVES, pl.Int64),
    (EvaluationColumn.FALSE_POSITIVES, pl.Int64),
    (EvaluationColumn.TRUE_NEGATIVES, pl.Int64),
    (EvaluationColumn.FALSE_NEGATIVES, pl.Int64),
    (EvaluationColumn.FALSE_POSITIVE_RATE, pl.Float64),
    (EvaluationColumn.FALSE_POSITIVE_RATE_STATUS, pl.String),
    (EvaluationColumn.TRUE_POSITIVE_RATE, pl.Float64),
    (EvaluationColumn.TRUE_POSITIVE_RATE_STATUS, pl.String),
    (EvaluationColumn.BALANCED_ACCURACY, pl.Float64),
    (EvaluationColumn.BALANCED_ACCURACY_STATUS, pl.String),
    (EvaluationColumn.MACRO_F1, pl.Float64),
    (EvaluationColumn.MACRO_F1_STATUS, pl.String),
    (EvaluationColumn.AUROC, pl.Float64),
    (EvaluationColumn.AUROC_STATUS, pl.String),
)

_COUNT_COLUMNS = (
    EvaluationColumn.TRUE_POSITIVES,
    EvaluationColumn.FALSE_POSITIVES,
    EvaluationColumn.TRUE_NEGATIVES,
    EvaluationColumn.FALSE_NEGATIVES,
)

_STATUS_COLUMNS = (
    EvaluationColumn.FALSE_POSITIVE_RATE_STATUS,
    EvaluationColumn.TRUE_POSITIVE_RATE_STATUS,
    EvaluationColumn.BALANCED_ACCURACY_STATUS,
    EvaluationColumn.MACRO_F1_STATUS,
    EvaluationColumn.AUROC_STATUS,
)


def _normalize_scores(
    scores: pl.DataFrame,
) -> pl.DataFrame:
    required = (
        EvaluationColumn.CLIENT_ID,
        EvaluationColumn.SCORE,
        EvaluationColumn.LABEL,
    )

    missing = tuple(column for column in required if column not in scores.columns)

    if missing:
        raise ValueError(f"Scores missing columns: {[column.value for column in missing]}")

    if scores.is_empty():
        raise ValueError("Cannot evaluate an empty score frame")

    normalized = scores.select(
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

    if normalized.get_column(EvaluationColumn.CLIENT_ID).is_null().any():
        raise ValueError("Score client IDs must not be null")

    score_values = normalized.get_column(EvaluationColumn.SCORE)

    if score_values.is_null().any() or score_values.is_nan().any() or score_values.is_infinite().any():
        raise ValueError("Scores must be finite")

    labels = normalized.get_column(EvaluationColumn.LABEL)

    if labels.is_null().any() or not labels.is_in((0, 1)).all():
        raise ValueError("Labels must be binary and non-null")

    return normalized


def _normalize_thresholds(
    thresholds: pl.DataFrame,
) -> pl.DataFrame:
    required = (
        EvaluationColumn.CLIENT_ID,
        EvaluationColumn.THRESHOLD,
    )

    missing = tuple(column for column in required if column not in thresholds.columns)

    if missing:
        raise ValueError(f"Thresholds missing columns: {[column.value for column in missing]}")

    normalized = thresholds.select(
        pl.col(EvaluationColumn.CLIENT_ID).cast(
            pl.String,
            strict=True,
        ),
        pl.col(EvaluationColumn.THRESHOLD).cast(
            pl.Float64,
            strict=True,
        ),
    )

    if normalized.get_column(EvaluationColumn.CLIENT_ID).is_null().any():
        raise ValueError("Threshold client IDs must not be null")

    if normalized.get_column(EvaluationColumn.CLIENT_ID).is_duplicated().any():
        raise ValueError("Threshold client IDs must be unique")

    non_null = normalized.get_column(EvaluationColumn.THRESHOLD).drop_nulls()

    if non_null.is_nan().any() or non_null.is_infinite().any():
        raise ValueError("Non-null thresholds must be finite")

    return normalized


def evaluate_operating_points(
    scores: pl.DataFrame,
    thresholds: pl.DataFrame,
    *,
    missing_threshold_policy: MissingThresholdPolicy,
) -> pl.DataFrame:
    normalized_scores = _normalize_scores(scores)
    normalized_thresholds = _normalize_thresholds(thresholds)

    scored_clients = normalized_scores.select(EvaluationColumn.CLIENT_ID).unique()

    extra_thresholds = normalized_thresholds.select(EvaluationColumn.CLIENT_ID).join(
        scored_clients,
        on=EvaluationColumn.CLIENT_ID,
        how="anti",
    )

    if not extra_thresholds.is_empty():
        raise ValueError(f"Thresholds contain unscored clients: {tuple(extra_thresholds.iter_rows(named=False))}")

    joined = normalized_scores.join(
        normalized_thresholds,
        on=EvaluationColumn.CLIENT_ID,
        how="left",
        validate="m:1",
    )

    missing_clients = (
        joined.filter(pl.col(EvaluationColumn.THRESHOLD).is_null())
        .select(EvaluationColumn.CLIENT_ID)
        .unique()
        .sort(EvaluationColumn.CLIENT_ID)
    )

    if not missing_clients.is_empty() and missing_threshold_policy is MissingThresholdPolicy.FAIL:
        raise ValueError(f"Missing thresholds for clients: {tuple(missing_clients.iter_rows(named=False))}")

    eligible = joined.filter(pl.col(EvaluationColumn.THRESHOLD).is_not_null())

    ineligible = joined.filter(pl.col(EvaluationColumn.THRESHOLD).is_null())

    if eligible.is_empty():
        metrics = _ineligible_rows(ineligible)
    elif ineligible.is_empty():
        metrics = _eligible_rows(eligible)
    else:
        metrics = pl.concat(
            (
                _eligible_rows(eligible),
                _ineligible_rows(ineligible),
            ),
            how="vertical",
        )

    result = metrics.join(
        _auroc_rows(normalized_scores),
        on=EvaluationColumn.CLIENT_ID,
        how="left",
        validate="1:1",
    )

    result = result.select(
        pl.col(column).cast(dtype, strict=True).alias(column) for column, dtype in _RESULT_FIELDS
    ).sort(EvaluationColumn.CLIENT_ID)

    _validate_result(result, scored_clients)

    return result


def _eligible_rows(
    frame: pl.DataFrame,
) -> pl.DataFrame:
    return (
        frame.lazy()
        .with_columns(
            _predicted_attack=(pl.col(EvaluationColumn.SCORE) > pl.col(EvaluationColumn.THRESHOLD)).cast(pl.Int64),
            _benign=(pl.col(EvaluationColumn.LABEL) == 0).cast(pl.Int64),
            _attack=(pl.col(EvaluationColumn.LABEL) == 1).cast(pl.Int64),
        )
        .with_columns(
            _tp=pl.col("_predicted_attack") * pl.col("_attack"),
            _fp=pl.col("_predicted_attack") * pl.col("_benign"),
            _tn=(1 - pl.col("_predicted_attack")) * pl.col("_benign"),
            _fn=(1 - pl.col("_predicted_attack")) * pl.col("_attack"),
        )
        .group_by(EvaluationColumn.CLIENT_ID)
        .agg(
            pl.col("_tp").sum().alias(EvaluationColumn.TRUE_POSITIVES),
            pl.col("_fp").sum().alias(EvaluationColumn.FALSE_POSITIVES),
            pl.col("_tn").sum().alias(EvaluationColumn.TRUE_NEGATIVES),
            pl.col("_fn").sum().alias(EvaluationColumn.FALSE_NEGATIVES),
        )
        .with_columns(
            _benign_total=(pl.col(EvaluationColumn.FALSE_POSITIVES) + pl.col(EvaluationColumn.TRUE_NEGATIVES)),
            _attack_total=(pl.col(EvaluationColumn.TRUE_POSITIVES) + pl.col(EvaluationColumn.FALSE_NEGATIVES)),
        )
        .with_columns(
            pl.when(pl.col("_benign_total") > 0)
            .then(pl.col(EvaluationColumn.FALSE_POSITIVES) / pl.col("_benign_total"))
            .otherwise(None)
            .alias(EvaluationColumn.FALSE_POSITIVE_RATE),
            pl.when(pl.col("_benign_total") > 0)
            .then(pl.lit(MetricStatus.AVAILABLE.value))
            .otherwise(pl.lit(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value))
            .alias(EvaluationColumn.FALSE_POSITIVE_RATE_STATUS),
            pl.when(pl.col("_attack_total") > 0)
            .then(pl.col(EvaluationColumn.TRUE_POSITIVES) / pl.col("_attack_total"))
            .otherwise(None)
            .alias(EvaluationColumn.TRUE_POSITIVE_RATE),
            pl.when(pl.col("_attack_total") > 0)
            .then(pl.lit(MetricStatus.AVAILABLE.value))
            .otherwise(pl.lit(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value))
            .alias(EvaluationColumn.TRUE_POSITIVE_RATE_STATUS),
        )
        .with_columns(
            pl.when((pl.col("_benign_total") > 0) & (pl.col("_attack_total") > 0))
            .then(
                (pl.col(EvaluationColumn.TRUE_POSITIVE_RATE) + 1.0 - pl.col(EvaluationColumn.FALSE_POSITIVE_RATE)) / 2.0
            )
            .otherwise(None)
            .alias(EvaluationColumn.BALANCED_ACCURACY),
            pl.when(pl.col("_benign_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value))
            .when(pl.col("_attack_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value))
            .otherwise(pl.lit(MetricStatus.AVAILABLE.value))
            .alias(EvaluationColumn.BALANCED_ACCURACY_STATUS),
            pl.when((pl.col("_benign_total") > 0) & (pl.col("_attack_total") > 0))
            .then(
                (
                    (
                        2.0
                        * pl.col(EvaluationColumn.TRUE_NEGATIVES)
                        / (
                            2.0 * pl.col(EvaluationColumn.TRUE_NEGATIVES)
                            + pl.col(EvaluationColumn.FALSE_POSITIVES)
                            + pl.col(EvaluationColumn.FALSE_NEGATIVES)
                        )
                    )
                    + (
                        2.0
                        * pl.col(EvaluationColumn.TRUE_POSITIVES)
                        / (
                            2.0 * pl.col(EvaluationColumn.TRUE_POSITIVES)
                            + pl.col(EvaluationColumn.FALSE_POSITIVES)
                            + pl.col(EvaluationColumn.FALSE_NEGATIVES)
                        )
                    )
                )
                / 2.0
            )
            .otherwise(None)
            .alias(EvaluationColumn.MACRO_F1),
            pl.when(pl.col("_benign_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value))
            .when(pl.col("_attack_total") == 0)
            .then(pl.lit(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS.value))
            .otherwise(pl.lit(MetricStatus.AVAILABLE.value))
            .alias(EvaluationColumn.MACRO_F1_STATUS),
        )
        .drop("_benign_total", "_attack_total")
        .collect()
    )


def _ineligible_rows(
    frame: pl.DataFrame,
) -> pl.DataFrame:
    status = MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value

    return (
        frame.select(EvaluationColumn.CLIENT_ID)
        .unique()
        .with_columns(
            *(pl.lit(None, dtype=pl.Int64).alias(column) for column in _COUNT_COLUMNS),
            pl.lit(None, dtype=pl.Float64).alias(EvaluationColumn.FALSE_POSITIVE_RATE),
            pl.lit(status).alias(EvaluationColumn.FALSE_POSITIVE_RATE_STATUS),
            pl.lit(None, dtype=pl.Float64).alias(EvaluationColumn.TRUE_POSITIVE_RATE),
            pl.lit(status).alias(EvaluationColumn.TRUE_POSITIVE_RATE_STATUS),
            pl.lit(None, dtype=pl.Float64).alias(EvaluationColumn.BALANCED_ACCURACY),
            pl.lit(status).alias(EvaluationColumn.BALANCED_ACCURACY_STATUS),
            pl.lit(None, dtype=pl.Float64).alias(EvaluationColumn.MACRO_F1),
            pl.lit(status).alias(EvaluationColumn.MACRO_F1_STATUS),
        )
    )


def _auroc_rows(
    scores: pl.DataFrame,
) -> pl.DataFrame:
    grouped = scores.group_by(
        EvaluationColumn.CLIENT_ID,
        maintain_order=True,
    ).agg(
        pl.col(EvaluationColumn.LABEL).alias("_labels"),
        pl.col(EvaluationColumn.SCORE).alias("_scores"),
    )

    client_ids: list[str] = []
    values: list[float | None] = []
    statuses: list[str] = []

    for client_raw, labels_raw, scores_raw in grouped.iter_rows(named=False):
        labels = np.asarray(
            labels_raw,
            dtype=np.int8,
        )

        client_scores = np.asarray(
            scores_raw,
            dtype=np.float64,
        )

        client_ids.append(str(client_raw))

        if np.unique(labels).size < 2:
            values.append(None)
            statuses.append(MetricStatus.UNAVAILABLE_SINGLE_CLASS.value)
        else:
            values.append(
                float(
                    roc_auc_score(
                        labels,
                        client_scores,
                    )
                )
            )
            statuses.append(MetricStatus.AVAILABLE.value)

    return pl.DataFrame(
        (
            pl.Series(
                EvaluationColumn.CLIENT_ID,
                client_ids,
                dtype=pl.String,
            ),
            pl.Series(
                EvaluationColumn.AUROC,
                values,
                dtype=pl.Float64,
            ),
            pl.Series(
                EvaluationColumn.AUROC_STATUS,
                statuses,
                dtype=pl.String,
            ),
        )
    )


def _validate_result(
    result: pl.DataFrame,
    scored_clients: pl.DataFrame,
) -> None:
    if result.height != scored_clients.height:
        raise ValueError("Evaluation must produce exactly one row per scored client")

    if result.get_column(EvaluationColumn.CLIENT_ID).is_duplicated().any():
        raise ValueError("Evaluation result contains duplicate client IDs")

    if any(result.get_column(column).is_null().any() for column in _STATUS_COLUMNS):
        raise ValueError("Metric statuses must never be null")

    valid_statuses = tuple(status.value for status in MetricStatus)

    for column in _STATUS_COLUMNS:
        if not result.get_column(column).is_in(valid_statuses).all():
            raise ValueError(f"Invalid metric status in {column.value}")

    auroc = result.get_column(EvaluationColumn.AUROC)
    auroc_status = result.get_column(EvaluationColumn.AUROC_STATUS)

    available = auroc_status == MetricStatus.AVAILABLE.value

    if auroc.filter(available).is_null().any():
        raise ValueError("Available AUROC rows require values")

    if auroc.filter(~available).is_not_null().any():
        raise ValueError("Unavailable AUROC rows must not contain values")

    ineligible = (
        result.get_column(EvaluationColumn.FALSE_POSITIVE_RATE_STATUS)
        == MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value
    )

    for column in _COUNT_COLUMNS:
        values = result.get_column(column)

        if values.filter(ineligible).is_not_null().any():
            raise ValueError("Ineligible confusion counts must be null")

        if values.filter(~ineligible).is_null().any():
            raise ValueError("Eligible confusion counts must be available")
