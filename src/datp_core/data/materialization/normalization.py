"""Shared out-of-core normalization for materialized Parquet artifacts."""

from __future__ import annotations

from pathlib import Path

import duckdb
import msgspec
import pyarrow.parquet as pq

from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    ConstantFeaturePolicy,
    DataFailureCode,
    MaterializedColumn,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
    SplitMembership,
)
from datp_core.data.contracts.materialization import DataLoadingConfig, NormalizationConfig, StandardNormalizationConfig
from datp_core.data.materialization.database import (
    fetch_scalar,
    quote_identifier,
    quote_literal,
    write_query_to_parquet,
)
from datp_core.data.materialization.errors import DataFailure


class NormalizationFeatureStatistics(msgspec.Struct, frozen=True):
    feature: str
    location: float
    scale: float


class NormalizationScopeStatistics(msgspec.Struct, frozen=True):
    client_id: str | None
    features: tuple[NormalizationFeatureStatistics, ...]


class NormalizationEvidence(msgspec.Struct, frozen=True):
    schema_version: str
    strategy: str
    fit_scope: str
    feature_names: tuple[str, ...]
    fitted_statistics: tuple[NormalizationScopeStatistics, ...]


def normalize_materialized_parquet(
    connection: duckdb.DuckDBPyConnection,
    source_path: Path,
    target_path: Path,
    feature_names: tuple[str, ...],
    config: NormalizationConfig,
    runtime: DataLoadingConfig,
) -> NormalizationEvidence:
    if not feature_names:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            "normalization requires feature columns",
            source_path=source_path,
            source_row_index=None,
        )
    schema_names = tuple(pq.ParquetFile(source_path).schema_arrow.names)
    missing = tuple(name for name in feature_names if name not in schema_names)
    if missing:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            "normalization features are missing from the materialized payload: " + ", ".join(missing),
            source_path=source_path,
            source_row_index=None,
        )
    fit_membership = _fit_membership(config.fit_scope)
    fit_count = _fit_population_count(connection, source_path, fit_membership)
    if fit_count == 0:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            "normalization fit population is empty",
            source_path=source_path,
            source_row_index=None,
        )
    statistics_table = "normalization_statistics"
    connection.execute(f"DROP TABLE IF EXISTS {quote_identifier(statistics_table)}")
    connection.execute(_statistics_query(source_path, statistics_table, feature_names, config, fit_membership))
    statistics = _read_evidence(connection, statistics_table, feature_names, config.fit_scope)
    _validate_scope_coverage(connection, source_path, statistics_table, config.fit_scope)
    _validate_statistics(connection, statistics_table, feature_names, config, source_path)
    _validate_out_of_range(connection, source_path, statistics_table, feature_names, config)
    query = _transformation_query(source_path, statistics_table, schema_names, feature_names, config)
    write_query_to_parquet(connection, query, target_path, runtime)
    return NormalizationEvidence(
        schema_version=ArtifactSchemaVersion.NORMALIZATION_V1.value,
        strategy=config.strategy.value,
        fit_scope=config.fit_scope.value,
        feature_names=feature_names,
        fitted_statistics=statistics,
    )


def encode_normalization_evidence(evidence: NormalizationEvidence) -> bytes:
    return msgspec.json.encode(evidence)


def _fetch_scalar(connection, query, source_path):
    result = connection.execute(query).fetchone()
    if result is None:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            "expected a scalar result but query returned no rows",
            source_path=source_path,
            source_row_index=None,
        )
    return int(result[0])


def _fit_membership(scope: NormalizationFitScope) -> SplitMembership:
    if scope in (NormalizationFitScope.GLOBAL_TRAIN, NormalizationFitScope.PER_CLIENT_TRAIN):
        return SplitMembership.TRAIN
    if scope is NormalizationFitScope.HISTORICAL_TRAIN:
        return SplitMembership.HISTORICAL_TRAINING
    raise DataFailure(
        DataFailureCode.CONFIGURATION,
        f"unsupported normalization fit scope '{scope.value}'",
        source_path=None,
        source_row_index=None,
    )


def _statistics_query(
    source_path: Path,
    table_name: str,
    feature_names: tuple[str, ...],
    config: NormalizationConfig,
    membership: SplitMembership,
) -> str:
    aggregations = ", ".join(
        expression for feature in feature_names for expression in _feature_aggregations(feature, config)
    )
    client_projection = (
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        if config.fit_scope is NormalizationFitScope.PER_CLIENT_TRAIN
        else ""
    )
    group_by = (
        f" GROUP BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        if config.fit_scope is NormalizationFitScope.PER_CLIENT_TRAIN
        else ""
    )
    return (
        f"CREATE TABLE {quote_identifier(table_name)} AS "
        f"SELECT {client_projection}{aggregations} "
        f"FROM read_parquet({quote_literal(source_path.as_posix())}) "
        f"WHERE {quote_identifier(MaterializedColumn.SPLIT.value)} = {quote_literal(membership.value)} "
        f"AND NOT {quote_identifier(MaterializedColumn.IS_ATTACK.value)}"
        f"{group_by}"
    )


def _feature_aggregations(feature: str, config: NormalizationConfig) -> tuple[str, str]:
    column = quote_identifier(feature)
    location_alias = quote_identifier(_location_column(feature))
    scale_alias = quote_identifier(_scale_column(feature))
    if config.strategy is NormalizationStrategy.MIN_MAX:
        return (f"min({column}) AS {location_alias}", f"max({column}) AS {scale_alias}")
    deviation = (
        "stddev_pop"
        if isinstance(config, StandardNormalizationConfig) and config.standard_deviation_ddof == 0
        else "stddev_samp"
    )
    return (f"avg({column}) AS {location_alias}", f"{deviation}({column}) AS {scale_alias}")


def _read_evidence(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    feature_names: tuple[str, ...],
    scope: NormalizationFitScope,
) -> tuple[NormalizationScopeStatistics, ...]:
    client_column = (
        quote_identifier(MaterializedColumn.CLIENT_ID.value)
        if scope is NormalizationFitScope.PER_CLIENT_TRAIN
        else "NULL"
    )
    selected = ", ".join(
        quote_identifier(column)
        for feature in feature_names
        for column in (_location_column(feature), _scale_column(feature))
    )
    order = (
        f" ORDER BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        if scope is NormalizationFitScope.PER_CLIENT_TRAIN
        else ""
    )
    rows = connection.execute(
        f"SELECT {client_column}, {selected} FROM {quote_identifier(table_name)}{order}"
    ).fetchall()
    result: list[NormalizationScopeStatistics] = []
    for row in rows:
        if any(value is None for value in row[1:]):
            raise DataFailure(
                DataFailureCode.NORMALIZATION,
                "normalization statistics contain null values",
                source_path=None,
                source_row_index=None,
            )
        features = tuple(
            NormalizationFeatureStatistics(
                feature=feature,
                location=float(row[1 + index * 2]),
                scale=float(row[2 + index * 2]),
            )
            for index, feature in enumerate(feature_names)
        )
        result.append(
            NormalizationScopeStatistics(
                client_id=None if row[0] is None else str(row[0]),
                features=features,
            )
        )
    return tuple(result)


def _fetch_count(connection: duckdb.DuckDBPyConnection, sql: str) -> int:
    row = connection.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def _validate_statistics(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    feature_names: tuple[str, ...],
    config: NormalizationConfig,
    source_path: Path,
) -> None:
    constant_predicates = " OR ".join(
        (
            f"{quote_identifier(_scale_column(feature))} = {quote_identifier(_location_column(feature))}"
            if config.strategy is NormalizationStrategy.MIN_MAX
            else f"{quote_identifier(_scale_column(feature))} = 0.0"
        )
        for feature in feature_names
    )
    constant_count = _fetch_count(
        connection,
        f"SELECT count(*) FROM {quote_identifier(table_name)} WHERE {constant_predicates}",
    )
    if constant_count and config.constant_feature_policy is ConstantFeaturePolicy.ERROR:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            "normalization encountered a constant fitted feature",
            source_path=source_path,
            source_row_index=None,
        )


def _validate_out_of_range(
    connection: duckdb.DuckDBPyConnection,
    source_path: Path,
    statistics_table: str,
    feature_names: tuple[str, ...],
    config: NormalizationConfig,
) -> None:
    predicate = _out_of_range_filter(feature_names, config)
    if predicate is None:
        return
    join = (
        f"JOIN {quote_identifier(statistics_table)} n ON "
        f"s.{quote_identifier(MaterializedColumn.CLIENT_ID.value)} = "
        f"n.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        if config.fit_scope is NormalizationFitScope.PER_CLIENT_TRAIN
        else f"CROSS JOIN {quote_identifier(statistics_table)} n"
    )
    count = _fetch_count(
        connection,
        f"SELECT count(*) FROM read_parquet({quote_literal(source_path.as_posix())}) s {join} WHERE {predicate}",
    )
    if count:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            f"{count} rows fall outside the fitted min-max range",
            source_path=source_path,
            source_row_index=None,
        )


def _transformation_query(
    source_path: Path,
    statistics_table: str,
    schema_names: tuple[str, ...],
    feature_names: tuple[str, ...],
    config: NormalizationConfig,
) -> str:
    features = frozenset(feature_names)
    projections = ", ".join(
        _normalized_projection(name, config) if name in features else f"s.{quote_identifier(name)}"
        for name in schema_names
    )
    join = (
        f"JOIN {quote_identifier(statistics_table)} n ON "
        f"s.{quote_identifier(MaterializedColumn.CLIENT_ID.value)} = "
        f"n.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        if config.fit_scope is NormalizationFitScope.PER_CLIENT_TRAIN
        else f"CROSS JOIN {quote_identifier(statistics_table)} n"
    )
    return f"SELECT {projections} FROM read_parquet({quote_literal(source_path.as_posix())}) s {join}"


def _normalized_projection(feature: str, config: NormalizationConfig) -> str:
    source = f"s.{quote_identifier(feature)}"
    location = f"n.{quote_identifier(_location_column(feature))}"
    scale = f"n.{quote_identifier(_scale_column(feature))}"
    if config.strategy is NormalizationStrategy.MIN_MAX:
        numerator = f"({source} - {location})"
        denominator = f"({scale} - {location})"
        normalized = f"({numerator} / {denominator})"
        if config.out_of_range_policy is OutOfRangePolicy.CLIP:
            normalized = f"greatest(0.0, least(1.0, {normalized}))"
        constant = f"({denominator} = 0.0)"
    else:
        normalized = f"(({source} - {location}) / {scale})"
        constant = f"({scale} = 0.0)"
    expression = f"CASE WHEN {constant} THEN 0.0 ELSE {normalized} END"
    return f"CAST({expression} AS DOUBLE) AS {quote_identifier(feature)}"


def _out_of_range_filter(feature_names: tuple[str, ...], config: NormalizationConfig) -> str | None:
    if config.strategy is not NormalizationStrategy.MIN_MAX or config.out_of_range_policy is not OutOfRangePolicy.ERROR:
        return None
    return " OR ".join(
        f"s.{quote_identifier(feature)} < n.{quote_identifier(_location_column(feature))} "
        f"OR s.{quote_identifier(feature)} > n.{quote_identifier(_scale_column(feature))}"
        for feature in feature_names
    )


def _location_column(feature: str) -> str:
    return f"__location__{feature}"


def _scale_column(feature: str) -> str:
    return f"__scale__{feature}"


def _fit_population_count(
    connection: duckdb.DuckDBPyConnection,
    source_path: Path,
    membership: SplitMembership,
) -> int:
    return _fetch_count(
        connection,
        f"SELECT count(*) FROM read_parquet({quote_literal(source_path.as_posix())}) "
        f"WHERE {quote_identifier(MaterializedColumn.SPLIT.value)} = {quote_literal(membership.value)} "
        f"AND NOT {quote_identifier(MaterializedColumn.IS_ATTACK.value)}",
    )


def _validate_scope_coverage(
    connection: duckdb.DuckDBPyConnection,
    source_path: Path,
    statistics_table: str,
    scope: NormalizationFitScope,
) -> None:
    if scope is not NormalizationFitScope.PER_CLIENT_TRAIN:
        return
    client_count = fetch_scalar(
        connection,
        f"SELECT count(DISTINCT {quote_identifier(MaterializedColumn.CLIENT_ID.value)}) "
        f"FROM read_parquet({quote_literal(source_path.as_posix())}) "
        f"WHERE NOT {quote_identifier(MaterializedColumn.IS_ATTACK.value)}",
    )
    stats_count = _fetch_scalar(connection, f"SELECT count(*) FROM {quote_identifier(statistics_table)}", source_path)
    if stats_count != client_count:
        raise DataFailure(
            DataFailureCode.NORMALIZATION,
            f"per-client normalization statistics cover {stats_count} clients; expected {client_count}",
            source_path=source_path,
            source_row_index=None,
        )
