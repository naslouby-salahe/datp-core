"""Compact aggregate split-manifest extraction and encoding."""

from __future__ import annotations

from pathlib import Path

import duckdb
import msgspec

from datp_core.core.hashing import Checksum, compute_file_checksum, compute_payload_checksum
from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    MaterializedArtifactShape,
    MaterializedColumn,
    SplitMembership,
)
from datp_core.data.contracts.materialization import WithinClientChronologicalSplitConfig
from datp_core.data.materialization.database import quote_identifier, quote_literal
from datp_core.data.materialization.models import DatasetMaterializationPlan, MaterializationEvidence
from datp_core.data.materialization.schema import MaterializedSchemaSpec, SchemaValidation


class SplitCount(msgspec.Struct, frozen=True):
    membership: str
    row_count: int
    benign_count: int
    attack_count: int


class ClientSplitCount(msgspec.Struct, frozen=True):
    client_id: str
    membership: str
    row_count: int
    benign_count: int
    attack_count: int


class ClassCount(msgspec.Struct, frozen=True):
    label: str
    row_count: int


class ClientChronologyRange(msgspec.Struct, frozen=True):
    client_id: str
    minimum_key: int
    maximum_key: int


class MaterializedSplitSummary(msgspec.Struct, frozen=True):
    schema_version: str
    dataset_id: str
    setup_id: str
    materialization_id: str
    source_checksum: str
    configuration_checksum: str
    artifact_checksum: str
    schema_checksum: str
    preprocessing_checksum: str
    artifact_shape: str
    total_rows: int
    split_counts: tuple[SplitCount, ...]
    client_split_counts: tuple[ClientSplitCount, ...]
    class_counts: tuple[ClassCount, ...]
    client_ids: tuple[str, ...]
    eligible_client_ids: tuple[str, ...]
    ineligible_client_ids: tuple[str, ...]
    attack_rows: int
    chronology_ranges: tuple[ClientChronologyRange, ...]
    materialization: MaterializationEvidence


def build_materialized_split_summary(
    path: Path,
    plan: DatasetMaterializationPlan,
    source_checksum: Checksum,
    schema_spec: MaterializedSchemaSpec,
    schema_validation: SchemaValidation,
    evidence: MaterializationEvidence,
    preprocessing_evidence: bytes,
) -> MaterializedSplitSummary:
    connection = duckdb.connect(":memory:")
    try:
        split_counts = _split_counts(connection, path)
        client_split_counts = _client_split_counts(connection, path)
        client_ids = tuple(
            str(row[0])
            for row in connection.execute(
                f"SELECT DISTINCT {quote_identifier(MaterializedColumn.CLIENT_ID.value)} "
                f"FROM read_parquet({quote_literal(path.as_posix())}) "
                f"ORDER BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
            ).fetchall()
        )
        calibration_membership = _calibration_membership(plan)
        eligible = tuple(
            client_id
            for client_id in client_ids
            if _benign_role_count(client_split_counts, client_id, calibration_membership)
            >= int(plan.eligibility.minimum_benign_calibration_count)
        )
        ineligible = tuple(client_id for client_id in client_ids if client_id not in eligible)
        attack_rows = sum(count.attack_count for count in split_counts)
        class_counts = _class_counts(connection, path, schema_spec.shape)
        chronology_ranges = _chronology_ranges(connection, path, schema_spec.shape)
    finally:
        connection.close()
    return MaterializedSplitSummary(
        schema_version=ArtifactSchemaVersion.SPLIT_SUMMARY_V1.value,
        dataset_id=plan.identity.dataset_id.value,
        setup_id=plan.identity.setup_id.value,
        materialization_id=plan.identity.materialization_id.value,
        source_checksum=source_checksum.value,
        configuration_checksum=plan.identity.configuration_checksum.value,
        artifact_checksum=compute_file_checksum(path).value,
        schema_checksum=schema_validation.checksum.value,
        preprocessing_checksum=compute_payload_checksum(preprocessing_evidence).value,
        artifact_shape=schema_spec.shape.value,
        total_rows=schema_validation.row_count,
        split_counts=split_counts,
        client_split_counts=client_split_counts,
        class_counts=class_counts,
        client_ids=client_ids,
        eligible_client_ids=eligible,
        ineligible_client_ids=ineligible,
        attack_rows=attack_rows,
        chronology_ranges=chronology_ranges,
        materialization=evidence,
    )


def encode_materialized_split_summary(summary: MaterializedSplitSummary) -> bytes:
    return msgspec.json.encode(summary)


def _split_counts(connection: duckdb.DuckDBPyConnection, path: Path) -> tuple[SplitCount, ...]:
    rows = connection.execute(
        "SELECT "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)}, count(*), "
        f"sum(CASE WHEN {quote_identifier(MaterializedColumn.IS_ATTACK.value)} THEN 0 ELSE 1 END), "
        f"sum(CASE WHEN {quote_identifier(MaterializedColumn.IS_ATTACK.value)} THEN 1 ELSE 0 END) "
        f"FROM read_parquet({quote_literal(path.as_posix())}) "
        f"GROUP BY {quote_identifier(MaterializedColumn.SPLIT.value)} "
        f"ORDER BY {quote_identifier(MaterializedColumn.SPLIT.value)}"
    ).fetchall()
    return tuple(
        SplitCount(
            membership=str(row[0]),
            row_count=int(row[1]),
            benign_count=int(row[2]),
            attack_count=int(row[3]),
        )
        for row in rows
    )


def _client_split_counts(connection: duckdb.DuckDBPyConnection, path: Path) -> tuple[ClientSplitCount, ...]:
    rows = connection.execute(
        "SELECT "
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)}, count(*), "
        f"sum(CASE WHEN {quote_identifier(MaterializedColumn.IS_ATTACK.value)} THEN 0 ELSE 1 END), "
        f"sum(CASE WHEN {quote_identifier(MaterializedColumn.IS_ATTACK.value)} THEN 1 ELSE 0 END) "
        f"FROM read_parquet({quote_literal(path.as_posix())}) GROUP BY "
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} ORDER BY "
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)}"
    ).fetchall()
    return tuple(
        ClientSplitCount(
            client_id=str(row[0]),
            membership=str(row[1]),
            row_count=int(row[2]),
            benign_count=int(row[3]),
            attack_count=int(row[4]),
        )
        for row in rows
    )


def _class_counts(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    shape: MaterializedArtifactShape,
) -> tuple[ClassCount, ...]:
    label_column = (
        MaterializedColumn.MULTICLASS_LABEL
        if shape is MaterializedArtifactShape.CICIOT2023
        else MaterializedColumn.ATTACK_FAMILY
        if shape is MaterializedArtifactShape.NBAIOT
        else None
    )
    if label_column is None:
        return ()
    rows = connection.execute(
        f"SELECT coalesce({quote_identifier(label_column.value)}, ''), count(*) "
        f"FROM read_parquet({quote_literal(path.as_posix())}) "
        f"GROUP BY {quote_identifier(label_column.value)} ORDER BY {quote_identifier(label_column.value)}"
    ).fetchall()
    return tuple(ClassCount(label=str(row[0]), row_count=int(row[1])) for row in rows)


def _chronology_ranges(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    shape: MaterializedArtifactShape,
) -> tuple[ClientChronologyRange, ...]:
    if shape is not MaterializedArtifactShape.EDGE_BENIGN_TEMPORAL:
        return ()
    rows = connection.execute(
        "SELECT "
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"min({quote_identifier(MaterializedColumn.CHRONOLOGY_KEY.value)}), "
        f"max({quote_identifier(MaterializedColumn.CHRONOLOGY_KEY.value)}) "
        f"FROM read_parquet({quote_literal(path.as_posix())}) "
        f"GROUP BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)} "
        f"ORDER BY {quote_identifier(MaterializedColumn.CLIENT_ID.value)}"
    ).fetchall()
    return tuple(
        ClientChronologyRange(
            client_id=str(row[0]),
            minimum_key=int(row[1]),
            maximum_key=int(row[2]),
        )
        for row in rows
    )


def _calibration_membership(plan: DatasetMaterializationPlan) -> SplitMembership:
    if isinstance(plan.split, WithinClientChronologicalSplitConfig):
        return SplitMembership.HISTORICAL_CALIBRATION
    return SplitMembership.CALIBRATION


def _benign_role_count(
    counts: tuple[ClientSplitCount, ...],
    client_id: str,
    membership: SplitMembership,
) -> int:
    for count in counts:
        if count.client_id == client_id and count.membership == membership.value:
            return count.benign_count
    return 0
