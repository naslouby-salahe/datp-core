"""Normalization fitting and transformation over materialized Parquet."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from datp_core.data.contracts.enums import NormalizationFitScope, NormalizationStrategy
from datp_core.data.preprocessing.models import (
    NormalizationEvidence,
    NormalizationFeatureStatistics,
    NormalizationScopeStatistics,
)


def normalize_materialized_parquet(
    source_path: Path,
    target_path: Path,
    *,
    feature_columns: tuple[str, ...],
    strategy: NormalizationStrategy,
    scope: NormalizationFitScope,
) -> NormalizationEvidence:
    if strategy not in {NormalizationStrategy.MIN_MAX, NormalizationStrategy.STANDARD}:
        raise ValueError(f"Unsupported normalization strategy: {strategy}")
    if scope not in {NormalizationFitScope.GLOBAL_TRAIN, NormalizationFitScope.PER_CLIENT_TRAIN}:
        raise ValueError(f"Unsupported normalization fit scope: {scope}")
    if not feature_columns:
        raise ValueError("Normalization requires at least one configured feature column")

    source = pl.scan_parquet(source_path).with_row_index("__datp_row_order")
    available_columns = set(source.collect_schema().names())
    required_columns = {"split", "is_attack", *feature_columns}
    if scope == NormalizationFitScope.PER_CLIENT_TRAIN:
        required_columns.add("client_id")
    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise ValueError(
            f"Materialized payload is missing normalization columns: {', '.join(missing_columns)}")

    train = source.filter((pl.col("split") == "train") & ~pl.col("is_attack"))
    statistics = _normalization_statistics(train, feature_columns, strategy, scope)
    if statistics.height == 0:
        raise ValueError("Normalization requires benign training rows")
    if scope == NormalizationFitScope.PER_CLIENT_TRAIN:
        observed_clients = set(source.select("client_id").unique().collect()["client_id"].to_list())
        fitted_clients = set(statistics["client_id"].to_list())
        missing_clients = sorted(observed_clients - fitted_clients)
        if missing_clients:
            raise ValueError(
                f"Normalization lacks benign training rows for clients: {', '.join(missing_clients)}")
        transformed = source.join(statistics.lazy(), on="client_id", how="left")
    else:
        transformed = source.join(statistics.lazy(), how="cross")
    transformed = transformed.with_columns(_normalization_expressions(feature_columns, strategy))
    transformed = transformed.sort("__datp_row_order").drop(
        "__datp_row_order", *_normalization_statistic_columns(feature_columns)
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    transformed.sink_parquet(target_path, compression="zstd")
    return NormalizationEvidence(
        strategy=strategy,
        scope=scope,
        feature_columns=feature_columns,
        fitted_statistics=_normalization_evidence_statistics(statistics, feature_columns, scope),
    )


def _normalization_statistics(
    train: pl.LazyFrame, feature_columns: tuple[str, ...], strategy: NormalizationStrategy, scope: NormalizationFitScope
) -> pl.DataFrame:
    aggregations = [
        expression.alias(f"__datp_{name}_{column}")
        for column in feature_columns
        for name, expression in (
            ("location", pl.col(column).min() if strategy ==
             NormalizationStrategy.MIN_MAX else pl.col(column).mean()),
            (
                "scale",
                pl.col(column).max() if strategy == NormalizationStrategy.MIN_MAX else pl.col(
                    column).std(ddof=0),
            ),
        )
    ]
    return (
        train.group_by("client_id").agg(aggregations).collect()
        if scope == NormalizationFitScope.PER_CLIENT_TRAIN
        else train.select(aggregations).collect()
    )


def _normalization_evidence_statistics(
    statistics: pl.DataFrame, feature_columns: tuple[str, ...], scope: str
) -> tuple[NormalizationScopeStatistics, ...]:
    return tuple(
        NormalizationScopeStatistics(
            client_id=str(row["client_id"]
                          ) if scope == NormalizationFitScope.PER_CLIENT_TRAIN else None,
            features=tuple(
                NormalizationFeatureStatistics(
                    feature=column,
                    location=float(row[f"__datp_location_{column}"]),
                    scale=float(row[f"__datp_scale_{column}"]),
                )
                for column in feature_columns
            ),
        )
        for row in statistics.iter_rows(named=True)
    )


def _normalization_expressions(feature_columns: tuple[str, ...], strategy: str) -> list[pl.Expr]:
    expressions: list[pl.Expr] = []
    for column in feature_columns:
        location = pl.col(f"__datp_location_{column}")
        scale = pl.col(f"__datp_scale_{column}")
        denominator = scale - location if strategy == NormalizationStrategy.MIN_MAX else scale
        expressions.append(
            pl.when(denominator == 0.0).then(0.0).otherwise(
                (pl.col(column) - location) / denominator).alias(column)
        )
    return expressions


def _normalization_statistic_columns(feature_columns: tuple[str, ...]) -> list[str]:
    return [f"__datp_{name}_{column}" for column in feature_columns for name in ("location", "scale")]
