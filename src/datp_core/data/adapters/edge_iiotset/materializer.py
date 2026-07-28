"""Benign-only streaming Edge-IIoTset materialization."""

from __future__ import annotations

import math
from pathlib import Path
from random import Random

import duckdb
import msgspec
import pyarrow as pa

from datp_core.data.contracts.constants import SECONDS_PER_DAY
from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    AttackAssignment,
    BoundaryRule,
    CategoryOrder,
    ChronologyRolloverPolicy,
    CsvColumnKind,
    DataFailureCode,
    DeduplicationPolicy,
    MaterializedArtifactShape,
    MaterializedColumn,
    NormalizationFitScope,
    SortDirection,
    SplitMembership,
)
from datp_core.data.contracts.materialization import RandomFractionalSplitConfig, WithinClientChronologicalSplitConfig
from datp_core.data.contracts.sources import SourceTreeConfig
from datp_core.data.contracts.values import ColumnName
from datp_core.data.materialization.database import (
    fetch_scalar,
    insert_record_batch,
    quote_identifier,
    quote_literal,
    write_query_to_parquet,
)
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import EdgeIIoTsetMaterializationPlan, MaterializationEvidence
from datp_core.data.materialization.semantics import (
    edge_content_digest,
    encoded_feature_name,
    normalize_label,
    split_membership_for_draw,
)
from datp_core.data.sources.csv import CsvBatchStream, CsvColumnSpec, CsvReadPlan
from datp_core.data.sources.models import SourceEntry, SourceInventory


class CategoryVocabulary(msgspec.Struct, frozen=True):
    column: str
    known_categories: tuple[str, ...]
    missing_token: str
    unknown_token: str
    encoded_feature_names: tuple[str, ...]


class EdgeVocabularyEvidence(msgspec.Struct, frozen=True):
    schema_version: str
    fit_membership: str
    columns: tuple[CategoryVocabulary, ...]


class EdgeMaterializationOutput(msgspec.Struct, frozen=True):
    evidence: MaterializationEvidence
    vocabulary: EdgeVocabularyEvidence
    numeric_feature_names: tuple[str, ...]
    all_feature_names: tuple[str, ...]


def materialize_edge_iiotset(
    connection: duckdb.DuckDBPyConnection,
    plan: EdgeIIoTsetMaterializationPlan,
    inventory: SourceInventory,
    target_path: Path,
) -> EdgeMaterializationOutput:
    _validate_plan(plan)
    _validate_fit_semantics(plan)
    numeric_names = tuple(column.value for column in plan.source.numeric_columns)
    categorical_names = tuple(column.value for column in plan.source.categorical_columns)
    _create_raw_table(connection, numeric_names, categorical_names)
    seen = excluded = valid = 0
    benign_label = normalize_label(plan.source.benign_label.value, plan.source.label_case_policy)
    for entry in inventory.executable_entries:
        client_id = _resolve_client_id(entry, inventory, plan)
        if client_id in tuple(client.value for client in plan.source.excluded_clients):
            continue
        stream = CsvBatchStream(
            CsvReadPlan(
                source_path=entry.source_path,
                columns=tuple(
                    CsvColumnSpec(ColumnName(column.value), CsvColumnKind.FLOAT64, False, False)
                    for column in plan.source.numeric_columns
                )
                + tuple(
                    CsvColumnSpec(column, CsvColumnKind.TEXT, True, True) for column in plan.source.categorical_columns
                )
                + (
                    CsvColumnSpec(plan.source.binary_label_column, CsvColumnKind.TEXT, False, True),
                    CsvColumnSpec(plan.source.multiclass_label_column, CsvColumnKind.TEXT, False, True),
                    CsvColumnSpec(plan.source.timestamp_column, CsvColumnKind.TEXT, False, True),
                ),
                invalid_row_policy=plan.source.invalid_row_policy,
                chunk_row_count=int(plan.runtime.chunk_row_count),
            )
        )
        for csv_batch in stream:
            expanded = _expand_batch(
                csv_batch.record_batch,
                entry.source_path,
                client_id,
                numeric_names,
                categorical_names,
                benign_label,
                plan,
            )
            insert_record_batch(connection, "raw_rows", expanded, "SELECT * FROM __datp_batch", ())
        report = stream.report
        seen += report.source_rows_seen
        excluded += report.excluded_rows
        valid += report.valid_rows
    if valid == 0:
        raise DataFailure(
            DataFailureCode.SOURCE_EMPTY,
            "Edge-IIoTset contains no valid benign source rows",
            source_path=None,
            source_row_index=None,
        )
    _create_canonical_table(connection, numeric_names, categorical_names)
    canonical_rows = fetch_scalar(connection, "SELECT count(*) FROM canonical_rows")
    if isinstance(plan.split, RandomFractionalSplitConfig):
        _assign_random_splits(connection, plan)
        chronology = False
    else:
        _assign_temporal_splits(connection, plan)
        chronology = True
    vocabulary = _fit_vocabulary(connection, plan, categorical_names)
    all_feature_names = numeric_names + tuple(
        feature for column in vocabulary.columns for feature in column.encoded_feature_names
    )
    query = _encoded_query(plan, numeric_names, vocabulary, chronology)
    written_rows = write_query_to_parquet(connection, query, target_path, plan.runtime)
    evidence = MaterializationEvidence(
        schema_version=ArtifactSchemaVersion.MATERIALIZED_V1.value,
        source_rows_seen=seen,
        excluded_rows=excluded,
        canonical_rows=canonical_rows,
        duplicate_rows_removed=valid - canonical_rows,
        conflicting_label_feature_group_count=0,
        written_rows=written_rows,
        encoded_feature_names=all_feature_names,
    )
    return EdgeMaterializationOutput(
        evidence=evidence,
        vocabulary=vocabulary,
        numeric_feature_names=numeric_names,
        all_feature_names=all_feature_names,
    )


def _validate_plan(plan: EdgeIIoTsetMaterializationPlan) -> None:
    if plan.split.attack_assignment is not AttackAssignment.EXCLUDE:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "Edge-IIoTset executable materialization is benign-only and must exclude attacks",
            source_path=None,
            source_row_index=None,
        )
    if isinstance(plan.split, RandomFractionalSplitConfig):
        if plan.split.deduplication is not DeduplicationPolicy.EXACT_WITHIN_CLIENT:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "Edge-IIoTset requires exact within-client deduplication",
                source_path=None,
                source_row_index=None,
            )
    elif isinstance(plan.split, WithinClientChronologicalSplitConfig):
        if (
            plan.split.sort_direction is not SortDirection.ASCENDING
            or plan.split.boundary_rule is not BoundaryRule.FLOOR
        ):
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "Edge-IIoTset temporal materialization requires ascending chronology and floor boundaries",
                source_path=None,
                source_row_index=None,
            )
    else:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            f"unsupported Edge-IIoTset split method '{plan.split.method.value}'",
            source_path=None,
            source_row_index=None,
        )
    expected_shape = (
        MaterializedArtifactShape.EDGE_BENIGN_TEMPORAL
        if isinstance(plan.split, WithinClientChronologicalSplitConfig)
        else MaterializedArtifactShape.EDGE_BENIGN_STATIC
    )
    if plan.artifact_shape is not expected_shape:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "Edge-IIoTset artifact shape does not match its split method",
            source_path=None,
            source_row_index=None,
        )


def _validate_fit_semantics(plan: EdgeIIoTsetMaterializationPlan) -> None:
    if isinstance(plan.split, RandomFractionalSplitConfig):
        if plan.categorical_encoding.vocabulary_fit_membership is not SplitMembership.TRAIN:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "random Edge-IIoTset materialization must fit categorical vocabulary on train only",
                source_path=None,
                source_row_index=None,
            )
        if plan.normalization.fit_scope not in (
            NormalizationFitScope.GLOBAL_TRAIN,
            NormalizationFitScope.PER_CLIENT_TRAIN,
        ):
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "random Edge-IIoTset normalization must fit on global or per-client train",
                source_path=None,
                source_row_index=None,
            )
        return
    if plan.categorical_encoding.vocabulary_fit_membership is not SplitMembership.HISTORICAL_TRAINING:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "temporal Edge-IIoTset materialization must fit categorical vocabulary on historical training only",
            source_path=None,
            source_row_index=None,
        )
    if plan.normalization.fit_scope is not NormalizationFitScope.HISTORICAL_TRAIN:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "temporal Edge-IIoTset normalization must fit on historical training only",
            source_path=None,
            source_row_index=None,
        )


def _create_raw_table(
    connection: duckdb.DuckDBPyConnection,
    numeric_names: tuple[str, ...],
    categorical_names: tuple[str, ...],
) -> None:
    columns = (
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)} VARCHAR NOT NULL",
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} VARCHAR NOT NULL",
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} BIGINT NOT NULL",
        "time_of_day_seconds DOUBLE NOT NULL",
        "content_digest BLOB NOT NULL",
        *(f"{quote_identifier(name)} DOUBLE NOT NULL" for name in numeric_names),
        *(f"{quote_identifier(name)} VARCHAR" for name in categorical_names),
    )
    connection.execute("CREATE TABLE raw_rows (" + ", ".join(columns) + ")")


def _resolve_client_id(
    entry: SourceEntry,
    inventory: SourceInventory,
    plan: EdgeIIoTsetMaterializationPlan,
) -> str:
    tree = _tree_for_entry(entry, plan)
    tree_root = (inventory.raw_data_root / tree.root.value).resolve()
    relative = entry.source_path.relative_to(tree_root)
    component = plan.source.client_identity.component_index
    if component >= len(relative.parts):
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "Edge-IIoTset client identity component is absent from the source path",
            source_path=entry.source_path,
            source_row_index=None,
        )
    return relative.parts[component]


def _tree_for_entry(entry: SourceEntry, plan: EdgeIIoTsetMaterializationPlan) -> SourceTreeConfig:
    for tree in plan.source.benign_trees:
        if tree.identifier == entry.source_tree_id:
            return tree
    raise DataFailure(
        DataFailureCode.CONFIGURATION,
        "Edge-IIoTset executable source is not owned by a benign tree",
        source_path=entry.source_path,
        source_row_index=None,
    )


def _expand_batch(
    batch: pa.RecordBatch,
    source_path: Path,
    client_id: str,
    numeric_names: tuple[str, ...],
    categorical_names: tuple[str, ...],
    benign_label: str,
    plan: EdgeIIoTsetMaterializationPlan,
) -> pa.RecordBatch:
    numeric_count = len(numeric_names)
    categorical_count = len(categorical_names)
    binary_index = numeric_count + categorical_count
    timestamp_index = binary_index + 2
    source_row_index_column = batch.column(timestamp_index + 1)
    clients: list[str] = []
    paths: list[str] = []
    source_indices: list[int] = []
    timestamps: list[float] = []
    digests: list[bytes] = []
    for row_index in range(batch.num_rows):
        binary_label = normalize_label(
            str(batch.column(binary_index)[row_index].as_py()),
            plan.source.label_case_policy,
        )
        if binary_label != benign_label:
            raise DataFailure(
                DataFailureCode.SOURCE_ROW,
                "attack-labeled row appeared in an executable benign Edge-IIoTset source",
                source_path=source_path,
                source_row_index=int(source_row_index_column[row_index].as_py()),
            )
        numeric = tuple(float(batch.column(index)[row_index].as_py()) for index in range(numeric_count))
        categorical = tuple(
            (
                None
                if batch.column(numeric_count + index)[row_index].as_py() is None
                else str(batch.column(numeric_count + index)[row_index].as_py())
            )
            for index in range(categorical_count)
        )
        clients.append(client_id)
        paths.append(source_path.as_posix())
        source_indices.append(int(source_row_index_column[row_index].as_py()))
        timestamps.append(
            _time_of_day_seconds(
                str(batch.column(timestamp_index)[row_index].as_py()),
                source_path,
                int(source_row_index_column[row_index].as_py()),
            )
        )
        digests.append(edge_content_digest(numeric, categorical, plan.runtime.row_digest))
    arrays: list[pa.Array] = [
        pa.array(clients, type=pa.string()),
        pa.array(paths, type=pa.string()),
        pa.array(source_indices, type=pa.int64()),
        pa.array(timestamps, type=pa.float64()),
        pa.array(digests, type=pa.binary()),
    ]
    arrays.extend(batch.column(index) for index in range(numeric_count + categorical_count))
    return pa.RecordBatch.from_arrays(
        arrays,
        (
            MaterializedColumn.CLIENT_ID.value,
            MaterializedColumn.SOURCE_PATH.value,
            MaterializedColumn.SOURCE_ROW_INDEX.value,
            "time_of_day_seconds",
            "content_digest",
            *numeric_names,
            *categorical_names,
        ),
    )


def _create_canonical_table(
    connection: duckdb.DuckDBPyConnection,
    numeric_names: tuple[str, ...],
    categorical_names: tuple[str, ...],
) -> None:
    equivalence = ", ".join(
        (quote_identifier(MaterializedColumn.CLIENT_ID.value),)
        + tuple(quote_identifier(name) for name in numeric_names + categorical_names)
    )
    connection.execute(
        "CREATE TABLE canonical_rows AS SELECT * EXCLUDE (__canonical_rank) FROM ("
        "SELECT *, row_number() OVER (PARTITION BY "
        f"{equivalence} ORDER BY {quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) AS __canonical_rank "
        "FROM raw_rows) WHERE __canonical_rank = 1"
    )


def _assign_random_splits(
    connection: duckdb.DuckDBPyConnection,
    plan: EdgeIIoTsetMaterializationPlan,
) -> None:
    split = plan.split
    if not isinstance(split, RandomFractionalSplitConfig):
        raise DataFailure(DataFailureCode.SPLIT, "random split plan required", source_path=None, source_row_index=None)
    connection.execute(
        "CREATE TABLE split_assignments ("
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} VARCHAR NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} BIGINT NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} VARCHAR NOT NULL, "
        f"PRIMARY KEY ({quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}))"
    )
    clients = tuple(
        str(row[0])
        for row in connection.execute(
            f"SELECT DISTINCT {quote_identifier(MaterializedColumn.CLIENT_ID.value)} "
            f"FROM canonical_rows ORDER BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        ).fetchall()
    )
    for client_id in clients:
        generator = Random(f"{int(split.seed.value)}:{client_id}")
        reader = connection.execute(
            "SELECT "
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} "
            "FROM canonical_rows WHERE "
            f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)} = ? "
            "ORDER BY content_digest, "
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}",
            (client_id,),
        ).fetch_record_batch(rows_per_batch=int(plan.runtime.chunk_row_count))
        for batch in reader:
            memberships = tuple(
                split_membership_for_draw(generator.random(), split.ratios).value for _ in range(batch.num_rows)
            )
            assignment = pa.RecordBatch.from_arrays(
                (batch.column(0), batch.column(1), pa.array(memberships, type=pa.string())),
                (
                    MaterializedColumn.SOURCE_PATH.value,
                    MaterializedColumn.SOURCE_ROW_INDEX.value,
                    MaterializedColumn.SPLIT.value,
                ),
            )
            insert_record_batch(connection, "split_assignments", assignment, "SELECT * FROM __datp_batch", ())
    connection.execute(
        "CREATE TABLE assigned_rows AS SELECT a.*, s."
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} FROM canonical_rows a JOIN split_assignments s ON "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} = "
        f"s.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} AND "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} = "
        f"s.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
    )


def _assign_temporal_splits(
    connection: duckdb.DuckDBPyConnection,
    plan: EdgeIIoTsetMaterializationPlan,
) -> None:
    split = plan.split
    if not isinstance(split, WithinClientChronologicalSplitConfig):
        raise DataFailure(
            DataFailureCode.SPLIT,
            "temporal split plan required",
            source_path=None,
            source_row_index=None,
        )
    if split.rollover_policy is ChronologyRolloverPolicy.FORBID_DECREASE:
        decreases = fetch_scalar(
            connection,
            "WITH ordered AS (SELECT time_of_day_seconds, lag(time_of_day_seconds) OVER ("
            f"PARTITION BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)} ORDER BY "
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) AS previous "
            "FROM canonical_rows) SELECT count(*) FROM ordered WHERE previous IS NOT NULL "
            "AND time_of_day_seconds < previous",
        )
        if decreases:
            raise DataFailure(
                DataFailureCode.SPLIT,
                "Edge-IIoTset chronology decreases under a forbid-decrease rollover policy",
                source_path=None,
                source_row_index=None,
            )
    rollover_increment = (
        "CASE WHEN previous_time IS NOT NULL AND time_of_day_seconds < previous_time THEN 1 ELSE 0 END"
        if split.rollover_policy is ChronologyRolloverPolicy.ADD_FIXED_PERIOD_ON_DECREASE
        else "0"
    )
    ratios = split.ratios
    historical_training_end = float(ratios.historical_training)
    historical_calibration_end = historical_training_end + float(ratios.historical_calibration)
    future_recalibration_end = historical_calibration_end + float(ratios.future_recalibration)
    connection.execute(
        "CREATE TABLE assigned_rows AS WITH provenance_ordered AS ("
        "SELECT *, lag(time_of_day_seconds) OVER ("
        f"PARTITION BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)} ORDER BY "
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) AS previous_time "
        "FROM canonical_rows), rollover_counted AS ("
        "SELECT *, sum("
        f"{rollover_increment}) OVER (PARTITION BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)} "
        f"ORDER BY {quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} ROWS UNBOUNDED PRECEDING) AS rollover_count "
        "FROM provenance_ordered), corrected AS ("
        "SELECT *, time_of_day_seconds + rollover_count * "
        f"{int(split.rollover_period_seconds)} AS corrected_time FROM rollover_counted), ranked AS ("
        "SELECT *, row_number() OVER ("
        f"PARTITION BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)} ORDER BY corrected_time, "
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) AS role_rank, "
        f"count(*) OVER (PARTITION BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}) AS client_count "
        "FROM corrected) SELECT * EXCLUDE (previous_time, rollover_count, corrected_time, role_rank, client_count), "
        "CAST(role_rank - 1 AS BIGINT) AS "
        f"{quote_identifier(MaterializedColumn.CHRONOLOGY_KEY.value)}, CASE "
        f"WHEN role_rank <= floor({historical_training_end} * client_count) "
        f"THEN {repr(SplitMembership.HISTORICAL_TRAINING.value)} "
        f"WHEN role_rank <= floor({historical_calibration_end} * client_count) "
        f"THEN {repr(SplitMembership.HISTORICAL_CALIBRATION.value)} "
        f"WHEN role_rank <= floor({future_recalibration_end} * client_count) "
        f"THEN {repr(SplitMembership.FUTURE_RECALIBRATION.value)} "
        f"ELSE {repr(SplitMembership.FUTURE_EVALUATION.value)} END AS "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} FROM ranked"
    )
    _validate_temporal_minimums(connection, split)


def _validate_temporal_minimums(
    connection: duckdb.DuckDBPyConnection,
    split: WithinClientChronologicalSplitConfig,
) -> None:
    requirements = (
        (SplitMembership.HISTORICAL_TRAINING, int(split.minimums.historical_training)),
        (SplitMembership.HISTORICAL_CALIBRATION, int(split.minimums.historical_calibration)),
        (SplitMembership.FUTURE_RECALIBRATION, int(split.minimums.future_recalibration)),
        (SplitMembership.FUTURE_EVALUATION, int(split.minimums.future_evaluation)),
    )
    clients = tuple(
        str(row[0])
        for row in connection.execute(
            f"SELECT DISTINCT {quote_identifier(MaterializedColumn.CLIENT_ID.value)} "
            f"FROM assigned_rows ORDER BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        ).fetchall()
    )
    for client_id in clients:
        for membership, minimum in requirements:
            observed = fetch_scalar(
                connection,
                "SELECT count(*) FROM assigned_rows WHERE "
                f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)} = ? AND "
                f"{quote_identifier(MaterializedColumn.SPLIT.value)} = ?",
                (client_id, membership.value),
            )
            if observed < minimum:
                raise DataFailure(
                    DataFailureCode.SPLIT,
                    f"temporal client '{client_id}' has {observed} rows for {membership.value}; requires {minimum}",
                    source_path=None,
                    source_row_index=None,
                )


def _fit_vocabulary(
    connection: duckdb.DuckDBPyConnection,
    plan: EdgeIIoTsetMaterializationPlan,
    categorical_names: tuple[str, ...],
) -> EdgeVocabularyEvidence:
    if plan.categorical_encoding.category_order is not CategoryOrder.LEXICOGRAPHIC:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "Edge-IIoTset supports lexicographic categorical vocabulary ordering",
            source_path=None,
            source_row_index=None,
        )
    missing = plan.source.missing_category_token.value
    unknown = plan.source.unknown_category_token.value
    columns: list[CategoryVocabulary] = []
    membership = plan.categorical_encoding.vocabulary_fit_membership
    for column in categorical_names:
        categories = tuple(
            str(row[0])
            for row in connection.execute(
                f"SELECT DISTINCT {quote_identifier(column)} FROM assigned_rows WHERE "
                f"{quote_identifier(MaterializedColumn.SPLIT.value)} = ? AND "
                f"{quote_identifier(column)} IS NOT NULL AND trim({quote_identifier(column)}) <> '' "
                f"ORDER BY {quote_identifier(column)}",
                (membership.value,),
            ).fetchall()
        )
        if missing in categories or unknown in categories:
            raise DataFailure(
                DataFailureCode.ENCODING,
                f"configured categorical sentinel collides with observed vocabulary for '{column}'",
                source_path=None,
                source_row_index=None,
            )
        encoded = tuple(
            encoded_feature_name(column, category, plan.categorical_encoding.encoded_feature_naming)
            for category in categories + (missing, unknown)
        )
        columns.append(
            CategoryVocabulary(
                column=column,
                known_categories=categories,
                missing_token=missing,
                unknown_token=unknown,
                encoded_feature_names=encoded,
            )
        )
    return EdgeVocabularyEvidence(
        schema_version=ArtifactSchemaVersion.CATEGORICAL_VOCABULARY_V1.value,
        fit_membership=membership.value,
        columns=tuple(columns),
    )


def _encoded_query(
    plan: EdgeIIoTsetMaterializationPlan,
    numeric_names: tuple[str, ...],
    vocabulary: EdgeVocabularyEvidence,
    chronology: bool,
) -> str:
    base = (
        f"a.{quote_identifier(MaterializedColumn.SPLIT.value)}, "
        f"a.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"false AS {quote_identifier(MaterializedColumn.IS_ATTACK.value)}, "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
    )
    if chronology:
        base += f", a.{quote_identifier(MaterializedColumn.CHRONOLOGY_KEY.value)}"
    numeric = ", ".join(f"a.{quote_identifier(name)}" for name in numeric_names)
    encoded = ", ".join(
        _one_hot_projection(column, category, feature_name)
        for column in vocabulary.columns
        for category, feature_name in zip(
            column.known_categories + (column.missing_token, column.unknown_token),
            column.encoded_feature_names,
            strict=True,
        )
    )
    projection = ", ".join(part for part in (base, numeric, encoded) if part)
    role_order = _edge_role_order(plan)
    order = (
        f"CASE a.{quote_identifier(MaterializedColumn.SPLIT.value)} "
        + " ".join(
            f"WHEN {quote_literal(membership.value)} THEN {index}" for index, membership in enumerate(role_order)
        )
        + " ELSE 999 END"
    )
    tail = (
        f", a.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"a.{quote_identifier(MaterializedColumn.CHRONOLOGY_KEY.value)}"
        if chronology
        else f", a.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
    )
    return f"SELECT {projection} FROM assigned_rows a ORDER BY {order}{tail}"


def _edge_role_order(plan: EdgeIIoTsetMaterializationPlan) -> tuple[SplitMembership, ...]:
    if isinstance(plan.split, RandomFractionalSplitConfig):
        return tuple(membership for membership, _ in plan.split.ratios.ordered())
    return (
        SplitMembership.HISTORICAL_TRAINING,
        SplitMembership.HISTORICAL_CALIBRATION,
        SplitMembership.FUTURE_RECALIBRATION,
        SplitMembership.FUTURE_EVALUATION,
    )


def _one_hot_projection(column: CategoryVocabulary, category: str, feature_name: str) -> str:
    source = f"a.{quote_identifier(column.column)}"
    normalized = (
        f"CASE WHEN {source} IS NULL OR trim({source}) = '' THEN {quote_literal(column.missing_token)} "
        f"WHEN {source} IN ("
        + ", ".join(quote_literal(value) for value in column.known_categories)
        + f") THEN {source} ELSE {quote_literal(column.unknown_token)} END"
        if column.known_categories
        else f"CASE WHEN {source} IS NULL OR trim({source}) = '' "
        f"THEN {quote_literal(column.missing_token)} ELSE {quote_literal(column.unknown_token)} END"
    )
    return (
        f"CAST(CASE WHEN ({normalized}) = {quote_literal(category)} THEN 1.0 ELSE 0.0 END AS DOUBLE) "
        f"AS {quote_identifier(feature_name)}"
    )


def _time_of_day_seconds(value: str, source_path: Path, source_row_index: int) -> float:
    candidate = value.strip().split()[-1]
    try:
        hours, minutes, seconds = candidate.split(":")
        parsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (IndexError, ValueError) as exc:
        raise DataFailure(
            DataFailureCode.SOURCE_ROW,
            "invalid Edge-IIoTset time-of-day value",
            source_path=source_path,
            source_row_index=source_row_index,
        ) from exc
    if not math.isfinite(parsed) or not 0.0 <= parsed < float(SECONDS_PER_DAY):
        raise DataFailure(
            DataFailureCode.SOURCE_ROW,
            "Edge-IIoTset time-of-day value is outside one day",
            source_path=source_path,
            source_row_index=source_row_index,
        )
    return parsed
