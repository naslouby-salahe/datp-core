"""Canonical streaming N-BaIoT materialization."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pyarrow as pa

from datp_core.data.adapters.nbaiot.partitioning import PartitionEvidence, apply_dirichlet_partition
from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    AttackAssignment,
    BoundaryRule,
    CsvColumnKind,
    DataFailureCode,
    DeduplicationPolicy,
    DeterministicOrdering,
    MaterializedColumn,
    SortDirection,
    SplitMembership,
    SplitLayout,
)
from datp_core.data.contracts.materialization import ChronologicalGappedSplitConfig, RandomFractionalSplitConfig
from datp_core.data.materialization.database import insert_record_batch, quote_identifier, write_query_to_parquet
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import (
    MaterializationEvidence,
    NBaIoTDirichletMaterializationPlan,
    NBaIoTPhysicalMaterializationPlan,
)
from datp_core.data.materialization.semantics import row_digest
from datp_core.data.sources.csv import CsvBatchStream, CsvColumnSpec, CsvReadPlan
from datp_core.data.sources.models import SourceInventory


type NBaIoTPlan = NBaIoTPhysicalMaterializationPlan | NBaIoTDirichletMaterializationPlan


def materialize_nbaiot(
    connection: duckdb.DuckDBPyConnection,
    plan: NBaIoTPlan,
    inventory: SourceInventory,
    target_path: Path,
) -> tuple[MaterializationEvidence, PartitionEvidence | None]:
    _validate_split(plan)
    feature_names = tuple(feature.value for feature in plan.source.feature_columns)
    _create_table(connection, feature_names)
    seen = excluded = valid = 0
    for source_ordinal, entry in enumerate(inventory.executable_entries):
        client_id, is_attack, attack_family = _classify_source(entry.source_path, inventory.raw_data_root, plan)
        stream = CsvBatchStream(
            CsvReadPlan(
                source_path=entry.source_path,
                columns=tuple(
                    CsvColumnSpec(
                        name=feature,
                        kind=CsvColumnKind.FLOAT64,
                        nullable=False,
                        strip_text=False,
                    )
                    for feature in plan.source.feature_columns
                ),
                invalid_row_policy=plan.source.invalid_row_policy,
                chunk_row_count=int(plan.runtime.chunk_row_count),
            )
        )
        for csv_batch in stream:
            expanded = _expand_batch(
                csv_batch.record_batch,
                entry.source_path,
                source_ordinal,
                client_id,
                is_attack,
                attack_family,
                feature_names,
                plan,
            )
            insert_record_batch(connection, "materialized_rows", expanded, "SELECT * FROM __datp_batch", ())
        report = stream.report
        seen += report.source_rows_seen
        excluded += report.excluded_rows
        valid += report.valid_rows
        if not is_attack:
            _assign_benign_source_split(connection, entry.source_path, report.valid_rows, plan)
    if valid == 0:
        raise DataFailure(
            DataFailureCode.SOURCE_EMPTY,
            "N-BaIoT contains no valid source rows",
            source_path=None,
            source_row_index=None,
        )
    partition = apply_dirichlet_partition(connection, plan) if isinstance(plan, NBaIoTDirichletMaterializationPlan) else None
    query = _final_query(feature_names, partition is not None)
    written_rows = write_query_to_parquet(connection, query, target_path, plan.runtime)
    evidence = MaterializationEvidence(
        schema_version=ArtifactSchemaVersion.MATERIALIZED_V1.value,
        source_rows_seen=seen,
        excluded_rows=excluded,
        canonical_rows=written_rows,
        duplicate_rows_removed=0,
        conflicting_label_feature_group_count=0,
        written_rows=written_rows,
        encoded_feature_names=feature_names,
    )
    return evidence, partition


def _validate_split(plan: NBaIoTPlan) -> None:
    if plan.split.attack_assignment is not AttackAssignment.TEST:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "N-BaIoT requires attack rows to be assigned to test",
            source_path=None,
            source_row_index=None,
        )
    if isinstance(plan.split, RandomFractionalSplitConfig):
        if plan.split.ratios.layout is not SplitLayout.STANDARD:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "N-BaIoT random materialization requires the standard train/calibration/test layout",
                source_path=None,
                source_row_index=None,
            )
        if plan.split.benign_ordering is not DeterministicOrdering.CONTENT_DIGEST:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "N-BaIoT random materialization requires content-digest ordering",
                source_path=None,
                source_row_index=None,
            )
        if plan.split.deduplication is not DeduplicationPolicy.NONE:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "N-BaIoT random materialization does not deduplicate rows",
                source_path=None,
                source_row_index=None,
            )
    elif isinstance(plan.split, ChronologicalGappedSplitConfig):
        if plan.split.boundary_rule is not BoundaryRule.FLOOR or plan.split.sort_direction is not SortDirection.ASCENDING:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "N-BaIoT chronological materialization requires floor boundaries and ascending source order",
                source_path=None,
                source_row_index=None,
            )
    else:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            f"unsupported N-BaIoT split method '{plan.split.method.value}'",
            source_path=None,
            source_row_index=None,
        )


def _create_table(connection: duckdb.DuckDBPyConnection, feature_names: tuple[str, ...]) -> None:
    features = ", ".join(f"{quote_identifier(name)} DOUBLE NOT NULL" for name in feature_names)
    connection.execute(
        "CREATE TABLE materialized_rows ("
        "source_ordinal BIGINT NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} VARCHAR, "
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)} VARCHAR NOT NULL, "
        "source_domain VARCHAR NOT NULL, "
        f"{quote_identifier(MaterializedColumn.IS_ATTACK.value)} BOOLEAN NOT NULL, "
        f"{quote_identifier(MaterializedColumn.ATTACK_FAMILY.value)} VARCHAR, "
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} VARCHAR NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} BIGINT NOT NULL, "
        "split_digest BLOB NOT NULL, "
        f"{features})"
    )


def _classify_source(source_path: Path, raw_data_root: Path, plan: NBaIoTPlan) -> tuple[str, bool, str | None]:
    tree_root = (raw_data_root / plan.source.tree.root.value).resolve()
    try:
        relative = source_path.relative_to(tree_root)
    except ValueError as exc:
        raise DataFailure(
            DataFailureCode.SOURCE_CONTAINMENT,
            "N-BaIoT source escapes the configured tree root",
            source_path=source_path,
            source_row_index=None,
        ) from exc
    component = plan.source.client_identity.component_index
    if component >= len(relative.parts):
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "N-BaIoT client identity component is absent from the source path",
            source_path=source_path,
            source_row_index=None,
        )
    client_id = relative.parts[component]
    if source_path.name == plan.source.benign_filename:
        return client_id, False, None
    if len(relative.parts) > component + 1:
        family = relative.parts[component + 1]
        if family in tuple(item.value for item in plan.source.attack_family_directories):
            return client_id, True, family
    raise DataFailure(
        DataFailureCode.SOURCE_CONTAINMENT,
        "N-BaIoT source does not match configured benign or attack-family path semantics",
        source_path=source_path,
        source_row_index=None,
    )


def _expand_batch(
    batch: pa.RecordBatch,
    source_path: Path,
    source_ordinal: int,
    client_id: str,
    is_attack: bool,
    attack_family: str | None,
    feature_names: tuple[str, ...],
    plan: NBaIoTPlan,
) -> pa.RecordBatch:
    splits = pa.array(
        tuple(SplitMembership.TEST.value if is_attack else None for _ in range(batch.num_rows)),
        type=pa.string(),
    )
    clients = pa.array(tuple(client_id for _ in range(batch.num_rows)), type=pa.string())
    attacks = pa.array(tuple(is_attack for _ in range(batch.num_rows)), type=pa.bool_())
    families = pa.array(tuple(attack_family for _ in range(batch.num_rows)), type=pa.string())
    paths = pa.array(tuple(source_path.as_posix() for _ in range(batch.num_rows)), type=pa.string())
    source_indices = batch.column(len(feature_names))
    digests: list[bytes] = []
    for row_index in range(batch.num_rows):
        numeric = tuple(float(batch.column(index)[row_index].as_py()) for index in range(len(feature_names)))
        digests.append(
            row_digest(
                numeric,
                (
                    source_path.as_posix(),
                    str(int(source_indices[row_index].as_py())),
                    str(int(plan.split.seed.value))
                    if isinstance(plan.split, RandomFractionalSplitConfig)
                    else plan.split.method.value,
                ),
                (is_attack,),
                plan.runtime.row_digest,
            )
        )
    arrays: list[pa.Array] = [
        pa.array(tuple(source_ordinal for _ in range(batch.num_rows)), type=pa.int64()),
        splits,
        clients,
        clients,
        attacks,
        families,
        paths,
        source_indices,
        pa.array(digests, type=pa.binary()),
    ]
    arrays.extend(batch.column(index) for index in range(len(feature_names)))
    return pa.RecordBatch.from_arrays(
        arrays,
        (
            "source_ordinal",
            MaterializedColumn.SPLIT.value,
            MaterializedColumn.CLIENT_ID.value,
            "source_domain",
            MaterializedColumn.IS_ATTACK.value,
            MaterializedColumn.ATTACK_FAMILY.value,
            MaterializedColumn.SOURCE_PATH.value,
            MaterializedColumn.SOURCE_ROW_INDEX.value,
            "split_digest",
            *feature_names,
        ),
    )


def _assign_benign_source_split(
    connection: duckdb.DuckDBPyConnection,
    source_path: Path,
    row_count: int,
    plan: NBaIoTPlan,
) -> None:
    if isinstance(plan.split, RandomFractionalSplitConfig):
        train_count = int(float(plan.split.ratios.ordered()[0][1]) * row_count)
        calibration_count = int(float(plan.split.ratios.ordered()[1][1]) * row_count)
        connection.execute(
            "UPDATE materialized_rows SET "
            f"{quote_identifier(MaterializedColumn.SPLIT.value)} = assigned.membership "
            "FROM (SELECT "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} AS row_index, "
            "CASE "
            f"WHEN row_number() OVER (ORDER BY split_digest, {quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) <= {train_count} "
            f"THEN {repr(SplitMembership.TRAIN.value)} "
            f"WHEN row_number() OVER (ORDER BY split_digest, {quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) <= {train_count + calibration_count} "
            f"THEN {repr(SplitMembership.CALIBRATION.value)} ELSE {repr(SplitMembership.TEST.value)} END AS membership "
            "FROM materialized_rows WHERE "
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} = ? AND NOT "
            f"{quote_identifier(MaterializedColumn.IS_ATTACK.value)}) assigned "
            f"WHERE materialized_rows.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} = ? AND "
            f"materialized_rows.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} = assigned.row_index",
            (source_path.as_posix(), source_path.as_posix()),
        )
        return
    split = plan.split
    if not isinstance(split, ChronologicalGappedSplitConfig):
        raise DataFailure(
            DataFailureCode.SPLIT,
            "chronological split contract required",
            source_path=source_path,
            source_row_index=None,
        )
    train_end = int(float(split.ratios.train) * row_count)
    first_gap_end = train_end + int(float(split.ratios.first_gap) * row_count)
    calibration_end = first_gap_end + int(float(split.ratios.calibration) * row_count)
    second_gap_end = calibration_end + int(float(split.ratios.second_gap) * row_count)
    connection.execute(
        "UPDATE materialized_rows SET "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} = CASE "
        f"WHEN {quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} <= {train_end} "
        f"THEN {repr(SplitMembership.TRAIN.value)} "
        f"WHEN {quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} <= {first_gap_end} THEN NULL "
        f"WHEN {quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} <= {calibration_end} "
        f"THEN {repr(SplitMembership.CALIBRATION.value)} "
        f"WHEN {quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} <= {second_gap_end} THEN NULL "
        f"ELSE {repr(SplitMembership.TEST.value)} END "
        f"WHERE {quote_identifier(MaterializedColumn.SOURCE_PATH.value)} = ? AND NOT "
        f"{quote_identifier(MaterializedColumn.IS_ATTACK.value)}",
        (source_path.as_posix(),),
    )


def _final_query(feature_names: tuple[str, ...], partitioned: bool) -> str:
    client_projection = (
        f"p.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
        if partitioned
        else f"m.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
    )
    join = (
        "JOIN partition_assignments p ON "
        f"m.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} = "
        f"p.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} AND "
        f"m.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} = "
        f"p.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
        if partitioned
        else ""
    )
    features = ", ".join(f"m.{quote_identifier(name)}" for name in feature_names)
    return (
        "SELECT "
        f"m.{quote_identifier(MaterializedColumn.SPLIT.value)}, "
        f"{client_projection} AS {quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"m.{quote_identifier(MaterializedColumn.IS_ATTACK.value)}, "
        f"m.{quote_identifier(MaterializedColumn.ATTACK_FAMILY.value)}, "
        f"m.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"m.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}, "
        f"{features} FROM materialized_rows m {join} "
        f"WHERE m.{quote_identifier(MaterializedColumn.SPLIT.value)} IS NOT NULL "
        "ORDER BY m.source_ordinal, "
        f"m.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
    )
