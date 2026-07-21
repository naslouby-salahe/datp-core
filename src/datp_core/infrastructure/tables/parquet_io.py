"""Parquet schema inspection and controlled Parquet reading/writing via PyArrow and Polars."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq
from attrs import define

from datp_core.domain.fingerprints import Fingerprint


@define(frozen=True, slots=True, kw_only=True)
class NormalizationEvidence:
    strategy: str
    scope: str
    feature_columns: tuple[str, ...]
    fitted_statistics: tuple[NormalizationScopeStatistics, ...]

    def encode(self) -> bytes:
        return json.dumps(
            {
                "schema_version": 1,
                "strategy": self.strategy,
                "scope": self.scope,
                "feature_columns": self.feature_columns,
                "fitted_statistics": [statistics.as_projection() for statistics in self.fitted_statistics],
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


@define(frozen=True, slots=True, kw_only=True)
class NormalizationFeatureStatistics:
    feature: str
    location: float
    scale: float

    def as_projection(self) -> dict[str, float | str]:
        return {"feature": self.feature, "location": self.location, "scale": self.scale}


@define(frozen=True, slots=True, kw_only=True)
class NormalizationScopeStatistics:
    client_id: str | None
    features: tuple[NormalizationFeatureStatistics, ...]

    def as_projection(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "features": [feature.as_projection() for feature in self.features],
        }


def write_dataframe_parquet(
    df: pl.DataFrame,
    target_path: Path,
    scientific_fingerprint: Fingerprint | None = None,
    compression: str = "zstd",
) -> None:
    """Write Polars DataFrame to Parquet with PyArrow schema validation and metadata injection."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_df = df.select(sorted(df.columns))
    arrow_table = sorted_df.to_arrow()

    existing_meta = arrow_table.schema.metadata or {}
    custom_meta = {
        b"schema_version": b"1",
        b"datp_fingerprint": (scientific_fingerprint.value.encode("utf-8") if scientific_fingerprint else b"none"),
    }
    merged_meta = {**existing_meta, **custom_meta}
    arrow_table = arrow_table.replace_schema_metadata(merged_meta)

    pq.write_table(arrow_table, target_path, compression=compression)


def read_dataframe_parquet(target_path: Path) -> pl.DataFrame:
    """Read Parquet file into Polars DataFrame with existence check."""
    if not target_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {target_path}")
    return pl.read_parquet(target_path)


def inspect_parquet_schema(target_path: Path) -> dict[str, str]:
    """Inspect PyArrow Parquet schema column types."""
    schema = pq.read_schema(target_path)
    return {name: str(dtype) for name, dtype in zip(schema.names, schema.types, strict=False)}


def normalize_materialized_parquet(
    source_path: Path,
    target_path: Path,
    *,
    feature_columns: tuple[str, ...],
    strategy: str,
    scope: str,
) -> NormalizationEvidence:
    """Fit configured normalization on benign training rows, then transform every materialized row."""
    if strategy not in {"min_max", "standard"}:
        raise ValueError(f"Unsupported normalization strategy: {strategy}")
    if scope not in {"global_train", "per_client_train"}:
        raise ValueError(f"Unsupported normalization fit scope: {scope}")
    if not feature_columns:
        raise ValueError("Normalization requires at least one configured feature column")

    source = pl.scan_parquet(source_path).with_row_index("__datp_row_order")
    available_columns = set(source.collect_schema().names())
    required_columns = {"split", "is_attack", *feature_columns}
    if scope == "per_client_train":
        required_columns.add("client_id")
    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise ValueError(f"Materialized payload is missing normalization columns: {', '.join(missing_columns)}")

    train = source.filter((pl.col("split") == "train") & ~pl.col("is_attack"))
    statistics = _normalization_statistics(train, feature_columns, strategy, scope)
    if statistics.height == 0:
        raise ValueError("Normalization requires benign training rows")
    if scope == "per_client_train":
        observed_clients = set(source.select("client_id").unique().collect()["client_id"].to_list())
        fitted_clients = set(statistics["client_id"].to_list())
        missing_clients = sorted(observed_clients - fitted_clients)
        if missing_clients:
            raise ValueError(f"Normalization lacks benign training rows for clients: {', '.join(missing_clients)}")
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
    train: pl.LazyFrame, feature_columns: tuple[str, ...], strategy: str, scope: str
) -> pl.DataFrame:
    aggregations = [
        expression.alias(f"__datp_{name}_{column}")
        for column in feature_columns
        for name, expression in (
            ("location", pl.col(column).min() if strategy == "min_max" else pl.col(column).mean()),
            ("scale", pl.col(column).max() if strategy == "min_max" else pl.col(column).std(ddof=0)),
        )
    ]
    return (
        train.group_by("client_id").agg(aggregations).collect()
        if scope == "per_client_train"
        else train.select(aggregations).collect()
    )


def _normalization_evidence_statistics(
    statistics: pl.DataFrame, feature_columns: tuple[str, ...], scope: str
) -> tuple[NormalizationScopeStatistics, ...]:
    return tuple(
        NormalizationScopeStatistics(
            client_id=str(row["client_id"]) if scope == "per_client_train" else None,
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
        denominator = scale - location if strategy == "min_max" else scale
        expressions.append(
            pl.when(denominator == 0.0).then(0.0).otherwise((pl.col(column) - location) / denominator).alias(column)
        )
    return expressions


def _normalization_statistic_columns(feature_columns: tuple[str, ...]) -> list[str]:
    return [f"__datp_{name}_{column}" for column in feature_columns for name in ("location", "scale")]
